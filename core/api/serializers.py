"""Conversão dos objetos do banco para dicionários (JSON de resposta)."""
from core import services


def cliente_json(cliente, com_veiculos=True):
    dados = {
        "id": cliente.id,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
        "cpf": cliente.cpf,
    }
    if com_veiculos:
        dados["veiculos"] = [veiculo_json(v, com_cliente=False) for v in cliente.veiculos.all()]
    return dados


def assinatura_json(assinatura):
    return {
        "id": assinatura.id,
        "veiculo_id": assinatura.veiculo_id,
        "servico": {"id": assinatura.servico_id, "nome": assinatura.servico.nome},
        "total_usos": assinatura.total_usos,
        "usos_restantes": assinatura.usos_restantes,
        "valor_mensal": assinatura.valor_mensal,
        "data_vencimento": assinatura.data_vencimento,
        "valida": assinatura.esta_valida(),
    }


def veiculo_json(veiculo, com_cliente=True):
    pacote = services.pacote_valido(veiculo)
    dados = {
        "id": veiculo.id,
        "placa": veiculo.placa,
        "modelo": veiculo.modelo,
        "porte": veiculo.porte,
        "pacote_valido": assinatura_json(pacote) if pacote else None,
    }
    if com_cliente:
        dados["cliente"] = {"id": veiculo.cliente_id, "nome": veiculo.cliente.nome}
    return dados


def servico_json(servico, porte=None):
    precos = {p.porte: p.valor for p in servico.precos.all()}
    dados = {
        "id": servico.id,
        "nome": servico.nome,
        "descricao": servico.descricao,
        "precos": precos,
    }
    if porte:
        dados["preco"] = precos.get(porte)
    return dados


def agendamento_json(agendamento):
    veiculo = agendamento.veiculo
    return {
        "id": agendamento.id,
        "data": agendamento.data,
        "turno": agendamento.turno,
        "status": agendamento.status,
        "veiculo": {"id": veiculo.id, "placa": veiculo.placa, "modelo": veiculo.modelo},
        "cliente": veiculo.cliente.nome,
    }


def pagamento_json(pagamento):
    return {
        "id": pagamento.id,
        "ordem_id": pagamento.ordem_id,
        "assinatura_id": pagamento.assinatura_id,
        "forma": pagamento.forma,
        "valor": pagamento.valor,
        "data": pagamento.data,
    }


def ordem_json(ordem):
    veiculo = ordem.veiculo
    pago = services.total_pago(ordem)
    return {
        "id": ordem.id,
        "data": ordem.data,
        "status": ordem.status,
        "veiculo": {
            "id": veiculo.id,
            "placa": veiculo.placa,
            "modelo": veiculo.modelo,
            "porte": veiculo.porte,
        },
        "cliente": {"id": veiculo.cliente_id, "nome": veiculo.cliente.nome},
        "funcionario": {"id": ordem.funcionario_id, "nome": ordem.funcionario.nome},
        "coberta_por_pacote": ordem.assinatura_id is not None,
        "itens": [
            {"servico_id": item.servico_id, "servico": item.servico.nome, "preco": item.preco}
            for item in ordem.itens.all()
        ],
        "valor_total": ordem.valor_total,
        "valor_pago": pago,
        "saldo": ordem.valor_total - pago,
        "valor_comissao": ordem.valor_comissao,
    }


def caixa_json(resumo):
    fechamento = resumo["fechamento"]
    return {
        "data": resumo["data"],
        "por_forma": resumo["por_forma"],
        "total_calculado": resumo["total"],
        "quantidade_pagamentos": resumo["quantidade"],
        "fechado": fechamento is not None,
        "fechamento": (
            {
                "valor_informado": fechamento.valor_informado,
                "total_calculado": fechamento.total_calculado,
                "diferenca": fechamento.diferenca,
                "responsavel": fechamento.usuario.nome,
            }
            if fechamento
            else None
        ),
    }
