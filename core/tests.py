"""
Testes automatizados do LavaFlow.

Verificam as principais regras de negócio e a API. Para rodar:
    python manage.py test --testrunner core.test_runner.LavaFlowTestRunner

O banco de testes é criado e apagado automaticamente pelo Django, então
os dados do banco real não são alterados.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from . import services
from .models import (
    Assinatura,
    Caixa,
    Cliente,
    OrdemServico,
    Porte,
    PrecoServico,
    Servico,
    Usuario,
    Veiculo,
)
from .services import RegraNegocioError


class BaseLavaFlow(TestCase):
    """Dados usados por todos os testes."""

    @classmethod
    def setUpTestData(cls):
        cls.hoje = timezone.localdate()
        cls.funcionario = Usuario.objects.create(
            nome="Pedro", email="pedro@teste.com", senha="x",
            perfil=Usuario.Perfil.FUNCIONARIO, percentual_comissao=Decimal("30.00"),
        )
        cls.atendente = Usuario.objects.create(
            nome="Ana", email="ana@teste.com", senha="x", perfil=Usuario.Perfil.ATENDENTE,
        )
        cliente = Cliente.objects.create(nome="João", telefone="(11) 98888-1001")
        cls.veiculo = Veiculo.objects.create(
            cliente=cliente, placa="ABC1D23", modelo="Onix", porte=Porte.MEDIO
        )
        cls.outro_veiculo = Veiculo.objects.create(
            cliente=cliente, placa="QWE2R34", modelo="HB20", porte=Porte.PEQUENO
        )
        cls.lavagem = Servico.objects.create(nome="Lavagem simples")
        cls.cera = Servico.objects.create(nome="Cera")
        for servico, precos in [(cls.lavagem, (35, 45, 60)), (cls.cera, (30, 40, 50))]:
            for porte, valor in zip(Porte.values, precos):
                PrecoServico.objects.create(servico=servico, porte=porte, valor=valor)

    def criar_pacote(self, vencimento_em_dias=20, usos_restantes=2):
        return Assinatura.objects.create(
            veiculo=self.veiculo, servico=self.lavagem, total_usos=4,
            usos_restantes=usos_restantes, valor_mensal=Decimal("160.00"),
            data_vencimento=self.hoje + timedelta(days=vencimento_em_dias),
        )

    def ordem_finalizada(self, servicos):
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, servicos)
        services.alterar_status(ordem, OrdemServico.Status.EM_ANDAMENTO)
        services.alterar_status(ordem, OrdemServico.Status.FINALIZADO)
        ordem.refresh_from_db()
        return ordem


class PrecoEOrdemServicoTests(BaseLavaFlow):
    def test_preco_depende_do_porte(self):
        self.assertEqual(services.preco_do_servico(self.lavagem, Porte.PEQUENO), Decimal("35.00"))
        self.assertEqual(services.preco_do_servico(self.lavagem, Porte.MEDIO), Decimal("45.00"))

    def test_abrir_ordem_calcula_total_pelo_porte(self):
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem, self.cera])
        self.assertEqual(ordem.valor_total, Decimal("85.00"))  # 45 + 40 (porte médio)
        self.assertEqual(ordem.status, OrdemServico.Status.AGUARDANDO)

    def test_preco_fica_gravado_na_ordem(self):
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem])
        PrecoServico.objects.filter(servico=self.lavagem, porte=Porte.MEDIO).update(valor=99)
        self.assertEqual(ordem.itens.get().preco, Decimal("45.00"))

    def test_responsavel_precisa_ser_funcionario(self):
        with self.assertRaises(RegraNegocioError):
            services.abrir_ordem(self.veiculo, self.atendente, [self.lavagem])

    def test_status_so_avanca(self):
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem])
        with self.assertRaises(RegraNegocioError):
            services.alterar_status(ordem, OrdemServico.Status.FINALIZADO)  # pulou etapa
        with self.assertRaises(RegraNegocioError):
            services.alterar_status(ordem, OrdemServico.Status.PAGO)  # só pelo pagamento


class PacoteMensalTests(BaseLavaFlow):
    def test_pacote_valido_cobre_servico_e_desconta_uso(self):
        pacote = self.criar_pacote(usos_restantes=2)
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem, self.cera])
        pacote.refresh_from_db()
        self.assertEqual(ordem.valor_total, Decimal("40.00"))  # só a cera é cobrada
        self.assertEqual(pacote.usos_restantes, 1)

    def test_pacote_vencido_nao_cobre(self):
        self.criar_pacote(vencimento_em_dias=-1)
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem])
        self.assertEqual(ordem.valor_total, Decimal("45.00"))

    def test_pacote_sem_usos_nao_cobre(self):
        self.criar_pacote(usos_restantes=0)
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem])
        self.assertEqual(ordem.valor_total, Decimal("45.00"))


class PagamentoEComissaoTests(BaseLavaFlow):
    def test_pagamento_total_quita_e_calcula_comissao(self):
        ordem = self.ordem_finalizada([self.lavagem])
        _, ordem, saldo = services.registrar_pagamento(ordem, "PIX", Decimal("45.00"))
        self.assertEqual(saldo, Decimal("0.00"))
        self.assertEqual(ordem.status, OrdemServico.Status.PAGO)
        self.assertEqual(ordem.valor_comissao, Decimal("13.50"))  # 30% de 45

    def test_pagamento_parcial_mantem_saldo(self):
        ordem = self.ordem_finalizada([self.lavagem])
        _, ordem, saldo = services.registrar_pagamento(ordem, "DINHEIRO", Decimal("20.00"))
        self.assertEqual(saldo, Decimal("25.00"))
        self.assertEqual(ordem.status, OrdemServico.Status.FINALIZADO)

    def test_pagamento_maior_que_saldo_e_recusado(self):
        ordem = self.ordem_finalizada([self.lavagem])
        with self.assertRaises(RegraNegocioError):
            services.registrar_pagamento(ordem, "PIX", Decimal("50.00"))

    def test_nao_paga_ordem_que_nao_terminou(self):
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem])
        with self.assertRaises(RegraNegocioError):
            services.registrar_pagamento(ordem, "PIX", Decimal("45.00"))

    def test_comissao_de_pacote_usa_valor_proporcional(self):
        self.criar_pacote()
        ordem = self.ordem_finalizada([self.lavagem])
        # Sem valor a pagar, a OS fica PAGO ao finalizar: 30% de (160 / 4) = 12,00
        self.assertEqual(ordem.status, OrdemServico.Status.PAGO)
        self.assertEqual(ordem.valor_comissao, Decimal("12.00"))

    def test_caixa_fechado_bloqueia_pagamento(self):
        ordem = self.ordem_finalizada([self.lavagem])
        Caixa.objects.create(
            usuario=self.atendente, data=self.hoje,
            total_calculado=Decimal("0"), valor_informado=Decimal("0"),
        )
        with self.assertRaises(RegraNegocioError):
            services.registrar_pagamento(ordem, "PIX", Decimal("45.00"))


class AgendamentoTests(BaseLavaFlow):
    @override_settings(CAPACIDADE_POR_TURNO=1)
    def test_turno_lotado_bloqueia_agendamento(self):
        amanha = self.hoje + timedelta(days=1)
        services.criar_agendamento(self.veiculo, amanha, "MANHA")
        with self.assertRaises(RegraNegocioError):
            services.criar_agendamento(self.outro_veiculo, amanha, "MANHA")

    def test_nao_agenda_data_passada(self):
        with self.assertRaises(RegraNegocioError):
            services.criar_agendamento(self.veiculo, self.hoje - timedelta(days=1), "TARDE")


class ApiTests(BaseLavaFlow):
    def test_cadastro_de_cliente_valido_retorna_201(self):
        resposta = self.client.post(
            "/api/clientes/",
            {"nome": "Carla", "telefone": "11977776666", "cpf": "529.982.247-25"},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()["telefone"], "(11) 97777-6666")

    def test_cadastro_de_cliente_invalido_retorna_400(self):
        resposta = self.client.post(
            "/api/clientes/",
            {"nome": "", "telefone": "123", "cpf": "111.111.111-11"},
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(set(resposta.json()["detalhes"]), {"nome", "telefone", "cpf"})

    def test_mudanca_de_status_invalida_retorna_422(self):
        ordem = services.abrir_ordem(self.veiculo, self.funcionario, [self.lavagem])
        resposta = self.client.patch(
            f"/api/ordens/{ordem.id}/status/", {"status": "PAGO"}, content_type="application/json"
        )
        self.assertEqual(resposta.status_code, 422)