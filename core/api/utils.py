"""
Ferramentas da API: leitura do JSON recebido, validação dos campos,
respostas padronizadas e tratamento de erros.
"""
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.services import RegraNegocioError


class ErroValidacao(Exception):
    

    def __init__(self, erros):
        super().__init__("Dados inválidos.")
        self.erros = erros


class NaoEncontrado(Exception):
    pass



# Respostas

def resposta(dados, status=200):
    return JsonResponse(
        dados,
        status=status,
        safe=False,
        encoder=DjangoJSONEncoder,
        json_dumps_params={"ensure_ascii": False},
    )


def resposta_erro(mensagem, status, detalhes=None):
    corpo = {"erro": mensagem}
    if detalhes:
        corpo["detalhes"] = detalhes
    return resposta(corpo, status=status)


def api(metodos):
  

    def decorador(view):
        @csrf_exempt
        @wraps(view)
        def envoltorio(request, *args, **kwargs):
            if request.method not in metodos:
                resp = resposta_erro(f"Método {request.method} não permitido.", 405)
                resp["Allow"] = ", ".join(metodos)
                return resp
            try:
                return view(request, *args, **kwargs)
            except ErroValidacao as erro:
                return resposta_erro("Dados inválidos.", 400, erro.erros)
            except NaoEncontrado as erro:
                return resposta_erro(str(erro), 404)
            except RegraNegocioError as erro:
                return resposta_erro(str(erro), 422)

        return envoltorio

    return decorador


def buscar(model, pk, nome):
    """Busca um registro pelo id ou gera 404 com mensagem amigável."""
    try:
        return model.objects.get(pk=pk)
    except (model.DoesNotExist, ValueError, TypeError):
        raise NaoEncontrado(f"{nome} {pk} não encontrado(a).")



# Leitura e validação do payload

def ler_json(request):
    try:
        dados = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ErroValidacao({"corpo": "JSON inválido."})
    if not isinstance(dados, dict):
        raise ErroValidacao({"corpo": "O corpo da requisição deve ser um objeto JSON."})
    return dados


PLACA_ANTIGA = re.compile(r"^[A-Z]{3}[0-9]{4}$")
PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")


def cpf_valido(numeros):
    """Confere os dois dígitos verificadores do CPF."""
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    digitos = [int(n) for n in numeros]
    for posicao in (9, 10):
        soma = sum(d * (posicao + 1 - i) for i, d in enumerate(digitos[:posicao]))
        verificador = (soma * 10) % 11 % 10
        if verificador != digitos[posicao]:
            return False
    return True


class Validador:
    """
    Valida os campos de um dicionário e acumula os erros, para devolver
    todos de uma vez. 
    """

    def __init__(self, dados):
        self.dados = dados
        self.erros = {}

    def _valor(self, campo, obrigatorio):
        valor = self.dados.get(campo)
        if isinstance(valor, str):
            valor = valor.strip()
        if valor is None or valor == "":
            if obrigatorio:
                self.erros[campo] = "Campo obrigatório."
            return None
        return valor

    def texto(self, campo, obrigatorio=True, max_len=None):
        valor = self._valor(campo, obrigatorio)
        if valor is None:
            return None
        if not isinstance(valor, str):
            self.erros[campo] = "Deve ser um texto."
            return None
        if max_len and len(valor) > max_len:
            self.erros[campo] = f"Máximo de {max_len} caracteres."
            return None
        return valor

    def inteiro(self, campo, obrigatorio=True, minimo=None, maximo=None):
        valor = self._valor(campo, obrigatorio)
        if valor is None:
            return None
        try:
            if isinstance(valor, bool):
                raise ValueError
            numero = int(valor)
        except (ValueError, TypeError):
            self.erros[campo] = "Deve ser um número inteiro."
            return None
        if minimo is not None and numero < minimo:
            self.erros[campo] = f"Deve ser no mínimo {minimo}."
            return None
        if maximo is not None and numero > maximo:
            self.erros[campo] = f"Deve ser no máximo {maximo}."
            return None
        return numero

    def dinheiro(self, campo, obrigatorio=True, permitir_zero=False):
        valor = self._valor(campo, obrigatorio)
        if valor is None:
            return None
        try:
            if isinstance(valor, bool):
                raise InvalidOperation
            numero = Decimal(str(valor).replace(",", "."))
            if not numero.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            self.erros[campo] = "Deve ser um valor numérico (ex.: 45.90)."
            return None
        if numero < 0 or (numero == 0 and not permitir_zero):
            self.erros[campo] = "Deve ser um valor maior que zero."
            return None
        if numero != numero.quantize(Decimal("0.01")):
            self.erros[campo] = "Use no máximo 2 casas decimais."
            return None
        return numero.quantize(Decimal("0.01"))

    def data(self, campo, obrigatorio=True):
        valor = self._valor(campo, obrigatorio)
        if valor is None:
            return None
        try:
            return date.fromisoformat(str(valor))
        except ValueError:
            self.erros[campo] = "Data inválida. Use o formato AAAA-MM-DD."
            return None

    def escolha(self, campo, opcoes, obrigatorio=True):
        valor = self._valor(campo, obrigatorio)
        if valor is None:
            return None
        valor = str(valor).upper()
        if valor not in opcoes:
            self.erros[campo] = f"Valor inválido. Use: {', '.join(opcoes)}."
            return None
        return valor

    def lista_ids(self, campo):
        valor = self.dados.get(campo)
        if not isinstance(valor, list) or not valor:
            self.erros[campo] = "Informe uma lista com pelo menos um id."
            return None
        if any(isinstance(v, bool) or not isinstance(v, int) for v in valor):
            self.erros[campo] = "A lista deve conter apenas números inteiros."
            return None
        if len(set(valor)) != len(valor):
            self.erros[campo] = "A lista não pode ter ids repetidos."
            return None
        return valor

    def telefone(self, campo, obrigatorio=True):
        valor = self.texto(campo, obrigatorio)
        if valor is None:
            return None
        numeros = re.sub(r"\D", "", valor)
        if len(numeros) not in (10, 11):
            self.erros[campo] = "Telefone deve ter DDD + número (10 ou 11 dígitos)."
            return None
        meio = 7 if len(numeros) == 11 else 6
        return f"({numeros[:2]}) {numeros[2:meio]}-{numeros[meio:]}"

    def cpf(self, campo, obrigatorio=False):
        valor = self.texto(campo, obrigatorio)
        if valor is None:
            return None
        numeros = re.sub(r"\D", "", valor)
        if not cpf_valido(numeros):
            self.erros[campo] = "CPF inválido."
            return None
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"

    def placa(self, campo, obrigatorio=True):
        valor = self.texto(campo, obrigatorio)
        if valor is None:
            return None
        placa = re.sub(r"[\s-]", "", valor).upper()
        if not (PLACA_ANTIGA.match(placa) or PLACA_MERCOSUL.match(placa)):
            self.erros[campo] = "Placa inválida. Use o formato ABC1234 ou ABC1D23."
            return None
        return placa

    def validar(self):
        if self.erros:
            raise ErroValidacao(self.erros)


def parametro_data(request, nome="data"):
    
    valor = request.GET.get(nome)
    if not valor:
        return timezone.localdate()
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ErroValidacao({nome: "Data inválida. Use o formato AAAA-MM-DD."})
