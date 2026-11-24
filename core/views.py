"""
Views das telas do LavaFlow (HTML com Bootstrap).

"""
from functools import wraps

from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import Usuario


def usuario_logado(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return None
    return Usuario.objects.filter(pk=usuario_id).first()


def login_obrigatorio(view=None, perfis=None):
    """
    Redireciona para o login quem não estiver autenticado. Se 'perfis' for
    informado, quem tiver outro perfil volta para a fila do dia.
    
    """

    def decorador(funcao):
        @wraps(funcao)
        def envoltorio(request, *args, **kwargs):
            usuario = usuario_logado(request)
            if usuario is None:
                return redirect("login")
            if perfis and usuario.perfil not in perfis:
                return redirect("fila")
            request.usuario = usuario
            return funcao(request, *args, **kwargs)

        return envoltorio

    return decorador(view) if view else decorador


# Telas de balcão: administrador e atendente (o funcionário só usa a fila)
BALCAO = [Usuario.Perfil.ADMIN, Usuario.Perfil.ATENDENTE]


@require_http_methods(["GET", "POST"])
def login(request):
    erro = None
    email = ""
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        senha = request.POST.get("senha", "")
        usuario = Usuario.objects.filter(email__iexact=email).first()
        if usuario and check_password(senha, usuario.senha):
            request.session.cycle_key()
            request.session["usuario_id"] = usuario.id
            return redirect("fila")
        erro = "E-mail ou senha incorretos."
    return render(request, "core/login.html", {"erro": erro, "email": email})


def logout(request):
    request.session.flush()
    return redirect("login")


@login_obrigatorio
def fila(request):
    return render(request, "core/fila.html", {"usuario": request.usuario, "pagina": "fila"})


@login_obrigatorio(perfis=BALCAO)
def nova_ordem(request):
    return render(request, "core/nova_ordem.html", {"usuario": request.usuario, "pagina": "nova_ordem"})


@login_obrigatorio(perfis=BALCAO)
def clientes(request):
    return render(request, "core/clientes.html", {"usuario": request.usuario, "pagina": "clientes"})


@login_obrigatorio(perfis=BALCAO)
def caixa(request):
    return render(request, "core/caixa.html", {"usuario": request.usuario, "pagina": "caixa"})
