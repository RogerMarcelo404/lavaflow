"""
Endpoints da API do LavaFlow.

Cada view segue as quatro etapas pedidas:
1. recebe a requisição (tela do sistema ou Postman);
2. valida e trata o payload (Validador);
3. persiste ou consulta no banco (models e services);
4. devolve a resposta em JSON (dados ou confirmação da ação).
"""
from django.db.models import Prefetch, Q

from core import services
from core.models import (
    Agendamento,
    Cliente,
    ItemOrdem,
    OrdemServico,
    Pagamento,
    Porte,
    Servico,
    Usuario,
    Veiculo,
)

from . import serializers as s
from .utils import (
    ErroValidacao,
    Validador,
    api,
    buscar,
    ler_json,
    parametro_data,
    resposta,
)



# Clientes

def _dados_cliente(request):
    v = Validador(ler_json(request))
    dados = {
        "nome": v.texto("nome", max_len=100),
        "telefone": v.telefone("telefone"),
        "cpf": v.cpf("cpf"),
    }
    v.validar()
    return dados


@api(["GET", "POST"])
def clientes(request):
    if request.method == "GET":
        consulta = Cliente.objects.prefetch_related("veiculos")
        busca = request.GET.get("busca", "").strip()
        if busca:
            consulta = consulta.filter(
                Q(nome__icontains=busca)
                | Q(telefone__icontains=busca)
                | Q(veiculos__placa__icontains=busca.replace("-", "").upper())
            ).distinct()
        return resposta([s.cliente_json(c) for c in consulta])

    dados = _dados_cliente(request)
    if dados["cpf"] and Cliente.objects.filter(cpf=dados["cpf"]).exists():
        raise ErroValidacao({"cpf": "Já existe um cliente com este CPF."})
    cliente = Cliente.objects.create(**dados)
    return resposta(s.cliente_json(cliente), status=201)


@api(["GET", "PUT", "DELETE"])
def cliente_detalhe(request, pk):
    cliente = buscar(Cliente, pk, "Cliente")

    if request.method == "GET":
        return resposta(s.cliente_json(cliente))

    if request.method == "PUT":
        dados = _dados_cliente(request)
        if dados["cpf"] and Cliente.objects.filter(cpf=dados["cpf"]).exclude(pk=pk).exists():
            raise ErroValidacao({"cpf": "Já existe um cliente com este CPF."})
        for campo, valor in dados.items():
            setattr(cliente, campo, valor)
        cliente.save()
        return resposta(s.cliente_json(cliente))

    if OrdemServico.objects.filter(veiculo__cliente=cliente).exists():
        raise services.RegraNegocioError(
            "O cliente possui ordens de serviço registradas e não pode ser excluído."
        )
    cliente.delete()
    return resposta({"mensagem": f"Cliente {pk} excluído."})



# Veículos

@api(["GET", "POST"])
def veiculos(request):
    if request.method == "GET":
        consulta = Veiculo.objects.select_related("cliente")
        placa = request.GET.get("placa", "").replace("-", "").strip().upper()
        if placa:
            consulta = consulta.filter(placa__icontains=placa)
        cliente_id = request.GET.get("cliente_id", "")
        if cliente_id:
            if not cliente_id.isdigit():
                raise ErroValidacao({"cliente_id": "Deve ser um número inteiro."})
            consulta = consulta.filter(cliente_id=int(cliente_id))
        return resposta([s.veiculo_json(v) for v in consulta[:50]])

    v = Validador(ler_json(request))
    cliente_id = v.inteiro("cliente_id", minimo=1)
    placa = v.placa("placa")
    modelo = v.texto("modelo", max_len=60)
    porte = v.escolha("porte", Porte.values)
    v.validar()

    if Veiculo.objects.filter(placa=placa).exists():
        raise ErroValidacao({"placa": "Já existe um veículo com esta placa."})
    cliente = buscar(Cliente, cliente_id, "Cliente")
    veiculo = Veiculo.objects.create(cliente=cliente, placa=placa, modelo=modelo, porte=porte)
    return resposta(s.veiculo_json(veiculo), status=201)


@api(["GET"])
def funcionarios(request):
    consulta = Usuario.objects.filter(perfil=Usuario.Perfil.FUNCIONARIO)
    return resposta(
        [
            {"id": u.id, "nome": u.nome, "percentual_comissao": u.percentual_comissao}
            for u in consulta
        ]
    )



# Serviços (com preço por porte)

@api(["GET"])
def servicos(request):
    porte = request.GET.get("porte", "").upper() or None
    if porte and porte not in Porte.values:
        raise ErroValidacao({"porte": f"Valor inválido. Use: {', '.join(Porte.values)}."})
    consulta = Servico.objects.prefetch_related("precos")
    return resposta([s.servico_json(servico, porte) for servico in consulta])



# Agendamentos

@api(["GET", "POST"])
def agendamentos(request):
    if request.method == "GET":
        data = parametro_data(request)
        consulta = Agendamento.objects.filter(data=data).select_related("veiculo__cliente")
        return resposta(
            {
                "data": data,
                "vagas": services.vagas_do_dia(data),
                "agendamentos": [s.agendamento_json(a) for a in consulta],
            }
        )

    v = Validador(ler_json(request))
    veiculo_id = v.inteiro("veiculo_id", minimo=1)
    data = v.data("data")
    turno = v.escolha("turno", Agendamento.Turno.values)
    v.validar()

    veiculo = buscar(Veiculo, veiculo_id, "Veículo")
    agendamento = services.criar_agendamento(veiculo, data, turno)
    return resposta(s.agendamento_json(agendamento), status=201)


@api(["POST"])
def agendamento_cancelar(request, pk):
    agendamento = buscar(Agendamento, pk, "Agendamento")
    services.cancelar_agendamento(agendamento)
    return resposta(s.agendamento_json(agendamento))



# Ordens de serviço e fila do dia

def _ordens_detalhadas():
    return OrdemServico.objects.select_related(
        "veiculo__cliente", "funcionario", "assinatura"
    ).prefetch_related(
        Prefetch("itens", queryset=ItemOrdem.objects.select_related("servico")),
        "pagamentos",
    )


@api(["GET"])
def fila(request):
    data = parametro_data(request)
    ordens = _ordens_detalhadas().filter(data=data).order_by("id")
    return resposta({"data": data, "ordens": [s.ordem_json(o) for o in ordens]})


@api(["POST"])
def ordens(request):
    v = Validador(ler_json(request))
    veiculo_id = v.inteiro("veiculo_id", minimo=1)
    funcionario_id = v.inteiro("funcionario_id", minimo=1)
    servicos_ids = v.lista_ids("servicos")
    v.validar()

    veiculo = buscar(Veiculo, veiculo_id, "Veículo")
    funcionario = buscar(Usuario, funcionario_id, "Funcionário")
    encontrados = {sv.id: sv for sv in Servico.objects.filter(id__in=servicos_ids)}
    faltando = [i for i in servicos_ids if i not in encontrados]
    if faltando:
        raise ErroValidacao({"servicos": f"Serviço(s) não encontrado(s): {faltando}."})

    ordem = services.abrir_ordem(veiculo, funcionario, [encontrados[i] for i in servicos_ids])
    ordem = _ordens_detalhadas().get(pk=ordem.pk)
    return resposta(s.ordem_json(ordem), status=201)


@api(["GET"])
def ordem_detalhe(request, pk):
    try:
        ordem = _ordens_detalhadas().get(pk=pk)
    except OrdemServico.DoesNotExist:
        buscar(OrdemServico, pk, "Ordem de serviço")  # gera o 404 padronizado
    return resposta(s.ordem_json(ordem))


@api(["PATCH"])
def ordem_status(request, pk):
    ordem = buscar(OrdemServico, pk, "Ordem de serviço")
    v = Validador(ler_json(request))
    novo_status = v.escolha("status", OrdemServico.Status.values)
    v.validar()

    services.alterar_status(ordem, novo_status)
    return resposta(s.ordem_json(_ordens_detalhadas().get(pk=pk)))



# Pagamentos e pacotes

@api(["POST"])
def pagamentos(request):
    v = Validador(ler_json(request))
    ordem_id = v.inteiro("ordem_id", minimo=1)
    forma = v.escolha("forma", Pagamento.Forma.values)
    valor = v.dinheiro("valor")
    v.validar()

    ordem = buscar(OrdemServico, ordem_id, "Ordem de serviço")
    pagamento, ordem, saldo = services.registrar_pagamento(ordem, forma, valor)
    return resposta(
        {
            "mensagem": "Pagamento registrado."
            + (" OS quitada e comissão calculada." if saldo == 0 else ""),
            "pagamento": s.pagamento_json(pagamento),
            "saldo_restante": saldo,
            "status_ordem": ordem.status,
            "valor_comissao": ordem.valor_comissao,
        },
        status=201,
    )


@api(["GET", "POST"])
def assinaturas(request):
    if request.method == "GET":
        veiculo_id = request.GET.get("veiculo_id")
        if not veiculo_id:
            raise ErroValidacao({"veiculo_id": "Informe o veículo (?veiculo_id=)."})
        veiculo = buscar(Veiculo, veiculo_id, "Veículo")
        consulta = veiculo.assinaturas.select_related("servico")
        return resposta([s.assinatura_json(a) for a in consulta])

    v = Validador(ler_json(request))
    veiculo_id = v.inteiro("veiculo_id", minimo=1)
    servico_id = v.inteiro("servico_id", minimo=1)
    total_usos = v.inteiro("total_usos", minimo=1, maximo=31)
    valor_mensal = v.dinheiro("valor_mensal")
    forma = v.escolha("forma", Pagamento.Forma.values)
    v.validar()

    veiculo = buscar(Veiculo, veiculo_id, "Veículo")
    servico = buscar(Servico, servico_id, "Serviço")
    assinatura = services.vender_pacote(veiculo, servico, total_usos, valor_mensal, forma)
    return resposta(s.assinatura_json(assinatura), status=201)



# Caixa e relatórios

@api(["GET"])
def caixa(request):
    data = parametro_data(request)
    return resposta(s.caixa_json(services.resumo_caixa(data)))


@api(["POST"])
def caixa_fechar(request):
    v = Validador(ler_json(request))
    usuario_id = v.inteiro("usuario_id", minimo=1)
    valor_informado = v.dinheiro("valor_informado", permitir_zero=True)
    data = v.data("data", obrigatorio=False)
    v.validar()

    usuario = buscar(Usuario, usuario_id, "Usuário")
    if usuario.perfil == Usuario.Perfil.FUNCIONARIO:
        raise services.RegraNegocioError("Apenas atendente ou administrador pode fechar o caixa.")
    data = data or parametro_data(request)
    services.fechar_caixa(usuario, data, valor_informado)
    return resposta(s.caixa_json(services.resumo_caixa(data)), status=201)


@api(["GET"])
def relatorio_comissoes(request):
    # Padrão: do primeiro dia do mês até hoje
    fim = parametro_data(request, "fim")
    inicio = parametro_data(request, "inicio") if request.GET.get("inicio") else fim.replace(day=1)
    if inicio > fim:
        raise ErroValidacao({"inicio": "A data inicial deve ser anterior à final."})
    linhas = services.relatorio_comissoes(inicio, fim)
    return resposta(
        {
            "inicio": inicio,
            "fim": fim,
            "funcionarios": [
                {
                    "funcionario_id": linha["funcionario_id"],
                    "nome": linha["funcionario__nome"],
                    "ordens": linha["ordens"],
                    "comissao": linha["comissao"],
                }
                for linha in linhas
            ],
        }
    )
