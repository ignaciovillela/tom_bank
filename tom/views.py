import re

from django import forms
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from tom import Data
from tom.models import Tarjeta, Transaccion


class TarjetaForm(forms.ModelForm):
    numero = forms.CharField(max_length=19)
    nombre = forms.CharField(max_length=50)
    cvv = forms.IntegerField(min_value=100, max_value=999)
    fecha_expiracion = forms.CharField(max_length=5)
    credito = forms.IntegerField(min_value=1)

    class Meta:
        model = Tarjeta
        fields = ['numero', 'nombre', 'cvv', 'fecha_expiracion', 'credito']

    def clean_numero(self):
        numero = self.cleaned_data['numero']
        if not re.match(r'\d{4}-\d{4}-\d{4}-\d{4}', numero):
            raise forms.ValidationError('Debe tener el siguiente formato:'
                                        ' 1234-5678-9012-3456')
        return numero.replace('-', '')

    def clean_fecha_expiracion(self):
        fecha_expiracion = self.cleaned_data['fecha_expiracion']
        try:
            assert re.match(r'\d{2}/\d{2}', fecha_expiracion)
            mes, anio = fecha_expiracion.split('/')
            assert int(mes) <= 12
        except:
            raise forms.ValidationError('Debe tener el siguiente formato:'
                                        ' MM/AA')
        return fecha_expiracion


class PagarTarjetaForm(forms.ModelForm):
    monto = forms.IntegerField(min_value=1)

    class Meta:
        model = Transaccion
        fields = ['monto']

    def __init__(self, *args, tarjeta, **kwargs):
        self.tarjeta = tarjeta
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance.pago_tarjeta(self.tarjeta)
        return super().save(commit)

    def clean_monto(self):
        return - self.cleaned_data['monto']


class RealizarPagoForm(forms.ModelForm):
    numero = forms.CharField(max_length=19)
    nombre = forms.CharField(max_length=50)
    cvv = forms.IntegerField(min_value=100, max_value=999, widget=forms.PasswordInput())
    fecha_expiracion = forms.CharField(max_length=5)

    class Meta:
        model = Transaccion
        fields = [
            'numero',
            'nombre',
            'cvv',
            'fecha_expiracion',
        ]

    def save(self, commit=True):
        if commit:
            self.instance.set_pagado(self.tarjeta)
        return super().save(commit)

    def clean_numero(self):
        numero = self.cleaned_data['numero']
        if not re.match(r'\d{4}-\d{4}-\d{4}-\d{4}', numero):
            raise forms.ValidationError('Debe tener el siguiente formato:'
                                        ' 1234-5678-9012-3456')
        return numero.replace('-', '')

    def clean_fecha_expiracion(self):
        fecha_expiracion = self.cleaned_data['fecha_expiracion']
        try:
            assert re.match(r'\d{2}/\d{2}', fecha_expiracion)
            mes, anio = fecha_expiracion.split('/')
            assert int(mes) <= 12
        except:
            raise forms.ValidationError('Debe tener el siguiente formato:'
                                        ' MM/AA')
        return fecha_expiracion

    def clean(self):
        try:
            self.tarjeta = Tarjeta.objects.get(
                numero=self.cleaned_data.get('numero'),
                nombre=self.cleaned_data.get('nombre'),
                cvv=self.cleaned_data.get('cvv'),
                fecha_expiracion=self.cleaned_data.get('fecha_expiracion'),
            )
        except Tarjeta.DoesNotExist:
            raise forms.ValidationError('No se encontró la tarjeta. Por favor, verifique que la información ingresada sea correcta.')
        result = self.tarjeta.can_pago(self.instance.monto)
        if result.is_err():
            raise forms.ValidationError(result.err())


def lista_tarjetas(request):
    if 'bloqueo' in request.GET:
        Data.BLOQUEO = request.GET['bloqueo'] == 'si'
        return redirect('lista_tarjetas')
    c = {
        'tarjetas': Tarjeta.objects.all(),
        'sistema_bloqueado': Data.BLOQUEO,
    }
    return render(request, 'lista_tarjetas.html', c)


def detalle_tarjeta(request, pk=None):
    tarjeta = transacciones = None
    if not pk:
        form = TarjetaForm(request.POST or None)
    else:
        tarjeta = Tarjeta.objects.get(id=pk)
        form = TarjetaForm(request.POST or None, instance=tarjeta)
        transacciones = tarjeta.transacciones.all()
    if form.is_valid():
        tarjeta = form.save()
        messages.success(request, f'Se {"actualizó" if pk else "agregó"} la tarjeta correctamente')
        return redirect('detalle_tarjeta', tarjeta.id)
    c = {
        'form': form,
        'tarjeta': tarjeta,
        'transacciones': transacciones,
    }
    return render(request, 'detalle_tarjeta.html', c)


def pagar_tarjeta(request, pk):
    tarjeta = Tarjeta.objects.get(id=pk)
    form = PagarTarjetaForm(
        request.POST or None,
        tarjeta=tarjeta,
    )
    if form.is_valid():
        form.save()
        messages.success(request, 'Se ha realizado el pago correctamente')
        return redirect('detalle_tarjeta', tarjeta.id)
    c = {
        'tarjeta': tarjeta,
        'form': form,
    }
    return render(request, 'pagar_tarjeta.html', c)


def realizar_pago(request, uuid):
    try:
        transaccion = Transaccion.objects.get(id=uuid, estado=Transaccion.Estados.PENDIENTE)
        if transaccion.get_expirado():
            raise transaccion.DoesNotExist
    except Transaccion.DoesNotExist:
        texto = 'Error: transacción no encontrada o no está pendiente'
        if 'timeout' in request.GET:
            texto = 'Pago expirado, por favor cierre esta ventana e intente realizar el pago nuevamente.'
        return HttpResponse(texto, status=400)
    form = RealizarPagoForm(request.POST or None, instance=transaccion)
    c = {
        'transaccion': transaccion,
        'form': form,
    }
    if form.is_valid():
        c['transaccion'] = form.save()
        return render(request, 'pago_realizado.html', c)
    return render(request, 'realizar_pago.html', c)


def api_realizar_pago(request):
    required_data = ['monto', 'detalle', 'success_url', 'error_url', 'redireccion_url']
    if request.method != 'GET':
        return JsonResponse({'error': 'Debe enviar los datos por GET'}, status=400)
    if not all(x in request.GET for x in required_data):
        return JsonResponse({'error': f'Se deben enviar los siguientes datos: {", ".join(required_data)}'}, status=400)
    transaccion = Transaccion.crear_transaccion_pendiente(
        request.GET['monto'],
        request.GET['detalle'],
        request.GET['success_url'],
        request.GET['error_url'],
        request.GET['redireccion_url'],
    )
    return JsonResponse({
        'id': transaccion.id,
        'monto': transaccion.monto,
        'detalle': transaccion.detalle,
        'fecha': transaccion.fecha.strftime('%d/%m/%Y'),
        'hora': transaccion.fecha.strftime('%H:%M'),
        'estado': transaccion.estado,
        'estado_display': transaccion.get_estado_display(),
        'success_url': transaccion.success_url,
        'error_url': transaccion.error_url,
        'redireccion_url': transaccion.redireccion_url,
        'url_pago': f'{request._current_scheme_host}{reverse("realizar_pago", args=[transaccion.id])}',
        'url_estado': f'{request._current_scheme_host}{reverse("api_verificar_pago")}?id={transaccion.id}',
    })


def api_verificar_pago(request):
    try:
        transaccion = Transaccion.objects.get(id=request.GET.get('id'))
    except Transaccion.DoesNotExist:
        return JsonResponse({'detalle': 'Transacción no encontrada.'}, status=400)
    transaccion.get_expirado()
    return JsonResponse({
        'id': transaccion.id,
        'tarjeta': transaccion.tarjeta and transaccion.tarjeta.numero_cifrado_display(),
        'monto': transaccion.monto,
        'detalle': transaccion.detalle,
        'fecha': transaccion.fecha,
        'fecha_expiracion': transaccion.fecha_expiracion,
        'segundos_restantes': transaccion.segundos_restantes,
        'fecha_pago': transaccion.fecha_pago,
        'estado': transaccion.estado,
        'estado_display': transaccion.get_estado_display(),
        'success_url': transaccion.success_url,
        'error_url': transaccion.error_url,
        'redireccion_url': transaccion.redireccion_url,
    })


def api_anular_pago(request, uuid):
    pass
