from django.urls import path

from . import views

urlpatterns = [
    path("", views.fila, name="fila"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("ordens/nova/", views.nova_ordem, name="nova_ordem"),
    path("clientes/", views.clientes, name="clientes"),
    path("caixa/", views.caixa, name="caixa"),
]
