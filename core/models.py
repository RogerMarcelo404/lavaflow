"""
Models do LavaFlow.

"""
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Porte(models.TextChoices):
    PEQUENO = "PEQUENO", "Pequeno"
    MEDIO = "MEDIO", "Médio"
    GRANDE = "GRANDE", "Grande"


class Usuario(models.Model):
    class Perfil(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        ATENDENTE = "ATENDENTE", "Atendente"
        FUNCIONARIO = "FUNCIONARIO", "Funcionário"

    nome = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    senha = models.CharField(max_length=255)  # hash pbkdf2_sha256
    perfil = models.CharField(max_length=20, choices=Perfil.choices)
    percentual_comissao = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    class Meta:
        managed = False
        db_table = "usuario"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "cliente"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Veiculo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="veiculos")
    placa = models.CharField(max_length=8, unique=True)
    modelo = models.CharField(max_length=60)
    porte = models.CharField(max_length=10, choices=Porte.choices)

    class Meta:
        managed = False
        db_table = "veiculo"
        ordering = ["placa"]

    def __str__(self):
        return f"{self.placa} - {self.modelo}"


class Servico(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    descricao = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "servico"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class PrecoServico(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name="precos")
    porte = models.CharField(max_length=10, choices=Porte.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "preco_servico"
        unique_together = [("servico", "porte")]

    def __str__(self):
        return f"{self.servico} ({self.porte}): R$ {self.valor}"


class Agendamento(models.Model):
    class Turno(models.TextChoices):
        MANHA = "MANHA", "Manhã"
        TARDE = "TARDE", "Tarde"

    class Status(models.TextChoices):
        AGENDADO = "AGENDADO", "Agendado"
        ATENDIDO = "ATENDIDO", "Atendido"
        CANCELADO = "CANCELADO", "Cancelado"

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name="agendamentos")
    data = models.DateField()
    turno = models.CharField(max_length=10, choices=Turno.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AGENDADO)

    class Meta:
        managed = False
        db_table = "agendamento"
        ordering = ["data", "turno", "id"]


class Assinatura(models.Model):
    """Pacote mensal de um veículo (ex.: 4 lavagens simples por mês)."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, related_name="assinaturas")
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name="assinaturas")
    total_usos = models.IntegerField()
    usos_restantes = models.IntegerField()
    valor_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()

    class Meta:
        managed = False
        db_table = "assinatura"
        ordering = ["-data_vencimento"]

    def esta_valida(self, data=None):
        """Regra: pacote vencido ou sem usos restantes não cobre a OS."""
        data = data or timezone.localdate()
        return self.data_vencimento >= data and self.usos_restantes > 0

    @property
    def valor_por_uso(self):
        """Valor proporcional de cada uso, usado no cálculo da comissão."""
        return self.valor_mensal / Decimal(self.total_usos)


class OrdemServico(models.Model):
    class Status(models.TextChoices):
        AGUARDANDO = "AGUARDANDO", "Aguardando"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        FINALIZADO = "FINALIZADO", "Finalizado"
        PAGO = "PAGO", "Pago"

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="ordens")
    funcionario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="ordens")
    assinatura = models.ForeignKey(
        Assinatura, on_delete=models.PROTECT, null=True, blank=True, related_name="ordens"
    )
    data = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AGUARDANDO)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valor_comissao = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "ordem_servico"
        ordering = ["-data", "id"]

    def __str__(self):
        return f"OS #{self.id} - {self.veiculo.placa}"


class ItemOrdem(models.Model):
    ordem = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="itens")
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name="itens")
    preco = models.DecimalField(max_digits=10, decimal_places=2)  # copiado na abertura

    class Meta:
        managed = False
        db_table = "item_ordem"
        ordering = ["id"]


class Pagamento(models.Model):
    class Forma(models.TextChoices):
        DINHEIRO = "DINHEIRO", "Dinheiro"
        PIX = "PIX", "PIX"
        CARTAO = "CARTAO", "Cartão"

    ordem = models.ForeignKey(
        OrdemServico, on_delete=models.PROTECT, null=True, blank=True, related_name="pagamentos"
    )
    assinatura = models.ForeignKey(
        Assinatura, on_delete=models.PROTECT, null=True, blank=True, related_name="pagamentos"
    )
    forma = models.CharField(max_length=10, choices=Forma.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "pagamento"
        ordering = ["-data"]


class Caixa(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="caixas")
    data = models.DateField(unique=True)
    total_calculado = models.DecimalField(max_digits=10, decimal_places=2)
    valor_informado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "caixa"
        ordering = ["-data"]

    @property
    def diferenca(self):
        return self.valor_informado - self.total_calculado
