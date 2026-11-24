"""
Painel administrativo do Django (/admin/)
"""
from django.contrib import admin

from .models import (
    Agendamento,
    Assinatura,
    Caixa,
    Cliente,
    ItemOrdem,
    OrdemServico,
    Pagamento,
    PrecoServico,
    Servico,
    Usuario,
    Veiculo,
)


class VeiculoInline(admin.TabularInline):
    model = Veiculo
    extra = 0


class PrecoInline(admin.TabularInline):
    model = PrecoServico
    extra = 0


class ItemInline(admin.TabularInline):
    model = ItemOrdem
    extra = 0


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "perfil", "percentual_comissao")
    list_filter = ("perfil",)
    exclude = ("senha",)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "cpf")
    search_fields = ("nome", "cpf", "veiculos__placa")
    inlines = [VeiculoInline]


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "descricao")
    inlines = [PrecoInline]


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ("id", "data", "veiculo", "funcionario", "status", "valor_total", "valor_comissao")
    list_filter = ("status", "data")
    inlines = [ItemInline]


admin.site.register([Veiculo, Agendamento, Assinatura, Pagamento, Caixa])
