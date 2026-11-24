from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("clientes/", views.clientes, name="clientes"),
    path("clientes/<int:pk>/", views.cliente_detalhe, name="cliente-detalhe"),
    path("veiculos/", views.veiculos, name="veiculos"),
    path("funcionarios/", views.funcionarios, name="funcionarios"),
    path("servicos/", views.servicos, name="servicos"),
    path("agendamentos/", views.agendamentos, name="agendamentos"),
    path("agendamentos/<int:pk>/cancelar/", views.agendamento_cancelar, name="agendamento-cancelar"),
    path("fila/", views.fila, name="fila"),
    path("ordens/", views.ordens, name="ordens"),
    path("ordens/<int:pk>/", views.ordem_detalhe, name="ordem-detalhe"),
    path("ordens/<int:pk>/status/", views.ordem_status, name="ordem-status"),
    path("pagamentos/", views.pagamentos, name="pagamentos"),
    path("assinaturas/", views.assinaturas, name="assinaturas"),
    path("caixa/", views.caixa, name="caixa"),
    path("caixa/fechar/", views.caixa_fechar, name="caixa-fechar"),
    path("relatorios/comissoes/", views.relatorio_comissoes, name="relatorio-comissoes"),
]
