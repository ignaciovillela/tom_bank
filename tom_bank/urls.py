from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from tom.views import (
    api_anular_pago, lista_tarjetas, pagar_tarjeta, detalle_tarjeta,
    api_realizar_pago, api_verificar_pago, realizar_pago,
)

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('lista_tarjetas'), permanent=True)),
    path('lista_tarjetas/', lista_tarjetas, name='lista_tarjetas'),
    path('agregar_tarjeta/', detalle_tarjeta, name='agregar_tarjeta'),
    path('detalle_tarjeta/<int:pk>/', detalle_tarjeta, name='detalle_tarjeta'),
    path('pagar_tarjeta/<int:pk>/', pagar_tarjeta, name='pagar_tarjeta'),

    path('realizar_pago/<uuid:uuid>/', realizar_pago, name='realizar_pago'),

    path('api/realizar_pago/', api_realizar_pago, name='api_realizar_pago'),
    path('api/anular_pago/', api_anular_pago, name='api_anular_pago'),
    path('api/verificar_pago/', api_verificar_pago, name='api_verificar_pago'),
]
