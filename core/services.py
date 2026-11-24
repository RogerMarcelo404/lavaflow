"""
Regras de negócio do LavaFlow.

"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from .models import (
    Agendamento,
    Assinatura,
    Caixa,
    ItemOrdem,
    OrdemServico,
    Pagamento,
    PrecoServico,
    Usuario,
)

ZERO = Decimal("0.00")


class RegraNegocioError(Exception):
    """Erro de regra de negócio, com mensagem pronta para mostrar ao usuário."""


def dinheiro(valor):
    """Arredonda um valor para 2 casas decimais (centavos)."""
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)



# Preço por porte

def preco_do_servico(servico, porte):
    """Regra: o preço do serviço depende do porte do veículo."""
    try:
        return PrecoServico.objects.get(servico=servico, porte=porte).valor
    except PrecoServico.DoesNotExist:
        raise RegraNegocioError(
            f"O serviço '{servico.nome}' não tem preço cadastrado para o porte {porte}."
        )



# Agendamento com limite por turno

def vagas_do_dia(data):
    """Retorna, para cada turno, a capacidade, as vagas ocupadas e as livres."""
    capacidade = settings.CAPACIDADE_POR_TURNO
    ocupadas = dict(
        Agendamento.objects.filter(data=data)
        .exclude(status=Agendamento.Status.CANCELADO)
        .values_list("turno")
        .annotate(total=Count("id"))
    )
    return {
        turno: {
            "capacidade": capacidade,
            "ocupadas": ocupadas.get(turno, 0),
            "livres": max(capacidade - ocupadas.get(turno, 0), 0),
        }
        for turno in Agendamento.Turno.values
    }


def criar_agendamento(veiculo, data, turno):
    """Regra: só agenda se o turno ainda tiver vaga."""
    if data < timezone.localdate():
        raise RegraNegocioError("Não é possível agendar em uma data que já passou.")

    ativos = Agendamento.objects.filter(data=data, turno=turno).exclude(
        status=Agendamento.Status.CANCELADO
    )
    if ativos.filter(veiculo=veiculo).exists():
        raise RegraNegocioError("Este veículo já tem agendamento nesta data e turno.")
    if ativos.count() >= settings.CAPACIDADE_POR_TURNO:
        raise RegraNegocioError("Turno lotado. Escolha outro turno ou outra data.")

    return Agendamento.objects.create(veiculo=veiculo, data=data, turno=turno)


def cancelar_agendamento(agendamento):
    if agendamento.status != Agendamento.Status.AGENDADO:
        raise RegraNegocioError("Só é possível cancelar agendamentos com status AGENDADO.")
    agendamento.status = Agendamento.Status.CANCELADO
    agendamento.save(update_fields=["status"])
    return agendamento



# Pacotes mensais

def pacote_valido(veiculo, data=None):
    """Retorna o pacote válido do veículo (não vencido e com usos) ou None."""
    data = data or timezone.localdate()
    return (
        Assinatura.objects.filter(
            veiculo=veiculo, data_vencimento__gte=data, usos_restantes__gt=0
        )
        .order_by("data_vencimento")
        .first()
    )


@transaction.atomic
def vender_pacote(veiculo, servico, total_usos, valor_mensal, forma):
    """Cria o pacote mensal (vencimento em 30 dias) e registra o pagamento."""
    if caixa_fechado():
        raise RegraNegocioError("O caixa de hoje já foi fechado.")
    if pacote_valido(veiculo):
        raise RegraNegocioError("Este veículo já possui um pacote válido.")
    preco_do_servico(servico, veiculo.porte)  # garante que o serviço atende o porte

    assinatura = Assinatura.objects.create(
        veiculo=veiculo,
        servico=servico,
        total_usos=total_usos,
        usos_restantes=total_usos,
        valor_mensal=valor_mensal,
        data_vencimento=timezone.localdate() + timedelta(days=30),
    )
    Pagamento.objects.create(assinatura=assinatura, forma=forma, valor=valor_mensal)
    return assinatura



# Ordem de serviço

@transaction.atomic
def abrir_ordem(veiculo, funcionario, servicos):
    """
    Abre uma OS:
    - calcula o preço de cada serviço pelo porte do veículo;
    - grava o preço no item (preserva o histórico);
    - se houver pacote válido para um dos serviços, esse item sai com preço 0
      e um uso do pacote é descontado.
    """
    if funcionario.perfil != Usuario.Perfil.FUNCIONARIO:
        raise RegraNegocioError("O responsável pela OS precisa ter perfil FUNCIONARIO.")
    if not servicos:
        raise RegraNegocioError("Informe pelo menos um serviço.")

    hoje = timezone.localdate()
    pacote = (
        Assinatura.objects.select_for_update()
        .filter(veiculo=veiculo, data_vencimento__gte=hoje, usos_restantes__gt=0)
        .order_by("data_vencimento")
        .first()
    )

    itens = []
    usou_pacote = False
    for servico in servicos:
        preco = preco_do_servico(servico, veiculo.porte)
        if pacote and not usou_pacote and servico.id == pacote.servico_id:
            preco = ZERO
            usou_pacote = True
        itens.append((servico, preco))

    ordem = OrdemServico.objects.create(
        veiculo=veiculo,
        funcionario=funcionario,
        assinatura=pacote if usou_pacote else None,
        data=hoje,
        status=OrdemServico.Status.AGUARDANDO,
        valor_total=sum((preco for _, preco in itens), ZERO),
    )
    ItemOrdem.objects.bulk_create(
        [ItemOrdem(ordem=ordem, servico=servico, preco=preco) for servico, preco in itens]
    )

    if usou_pacote:
        pacote.usos_restantes -= 1
        pacote.save(update_fields=["usos_restantes"])

    # Se o veículo estava agendado para hoje, o agendamento passa a ATENDIDO
    Agendamento.objects.filter(
        veiculo=veiculo, data=hoje, status=Agendamento.Status.AGENDADO
    ).update(status=Agendamento.Status.ATENDIDO)

    return ordem


# Fluxo permitido: AGUARDANDO -> EM_ANDAMENTO -> FINALIZADO -> PAGO
PROXIMO_STATUS = {
    OrdemServico.Status.AGUARDANDO: OrdemServico.Status.EM_ANDAMENTO,
    OrdemServico.Status.EM_ANDAMENTO: OrdemServico.Status.FINALIZADO,
}


@transaction.atomic
def alterar_status(ordem, novo_status):
    if novo_status == OrdemServico.Status.PAGO:
        raise RegraNegocioError(
            "O status PAGO é definido automaticamente quando o pagamento é registrado."
        )
    if PROXIMO_STATUS.get(ordem.status) != novo_status:
        raise RegraNegocioError(f"Não é possível mudar de {ordem.status} para {novo_status}.")

    ordem.status = novo_status
    ordem.save(update_fields=["status"])

    # Regra: se não há valor a pagar (coberta pelo pacote), a OS é concluída
    if novo_status == OrdemServico.Status.FINALIZADO and ordem.valor_total == ZERO:
        _concluir_ordem(ordem)
    return ordem



# Comissão e pagamento

def calcular_comissao(ordem):
    """
    Regra: comissão = valor-base x percentual do funcionário.
    Em OS coberta por pacote, o serviço coberto entra pelo valor proporcional
    (valor mensal / total de usos).
    """
    base = ordem.valor_total
    if ordem.assinatura_id:
        base += ordem.assinatura.valor_por_uso
    percentual = ordem.funcionario.percentual_comissao or ZERO
    return dinheiro(base * percentual / Decimal("100"))


def _concluir_ordem(ordem):
    ordem.status = OrdemServico.Status.PAGO
    ordem.valor_comissao = calcular_comissao(ordem)
    ordem.save(update_fields=["status", "valor_comissao"])


def total_pago(ordem):
    return ordem.pagamentos.aggregate(total=Sum("valor"))["total"] or ZERO


def caixa_fechado(data=None):
    return Caixa.objects.filter(data=data or timezone.localdate()).exists()


@transaction.atomic
def registrar_pagamento(ordem, forma, valor):
    """Registra um pagamento (pode ser parcial). Quando quita, a OS vira PAGO."""
    ordem = OrdemServico.objects.select_for_update().get(pk=ordem.pk)

    if caixa_fechado():
        raise RegraNegocioError("O caixa de hoje já foi fechado.")
    if ordem.status == OrdemServico.Status.PAGO:
        raise RegraNegocioError("Esta OS já está paga.")
    if ordem.status != OrdemServico.Status.FINALIZADO:
        raise RegraNegocioError("Só é possível registrar pagamento de uma OS finalizada.")

    saldo = ordem.valor_total - total_pago(ordem)
    if valor > saldo:
        raise RegraNegocioError(f"O valor informado é maior que o saldo da OS (R$ {saldo}).")

    pagamento = Pagamento.objects.create(ordem=ordem, forma=forma, valor=valor)
    saldo -= valor
    if saldo == ZERO:
        _concluir_ordem(ordem)
    return pagamento, ordem, saldo



# Caixa e relatórios

def resumo_caixa(data):
    pagamentos = Pagamento.objects.filter(data__date=data)
    por_forma = {forma: ZERO for forma in Pagamento.Forma.values}
    for linha in pagamentos.values("forma").annotate(total=Sum("valor")):
        por_forma[linha["forma"]] = linha["total"]
    return {
        "data": data,
        "por_forma": por_forma,
        "total": sum(por_forma.values(), ZERO),
        "quantidade": pagamentos.count(),
        "fechamento": Caixa.objects.filter(data=data).first(),
    }


@transaction.atomic
def fechar_caixa(usuario, data, valor_informado):
    if Caixa.objects.filter(data=data).exists():
        raise RegraNegocioError("O caixa deste dia já foi fechado.")
    total = resumo_caixa(data)["total"]
    return Caixa.objects.create(
        usuario=usuario, data=data, total_calculado=total, valor_informado=valor_informado
    )


def relatorio_comissoes(inicio, fim):
    return list(
        OrdemServico.objects.filter(status=OrdemServico.Status.PAGO, data__range=(inicio, fim))
        .values("funcionario_id", "funcionario__nome")
        .annotate(ordens=Count("id"), comissao=Sum("valor_comissao"))
        .order_by("-comissao")
    )
