import re
import uuid
from datetime import date, datetime, timedelta, timezone

from django.db import models
from django.db.models import Case, Sum, When
from result import Err, Ok

from tom import Data
from tom.async_process import call_func_with_delay, make_request


class Tarjeta(models.Model):
    numero = models.IntegerField(unique=True, auto_created=True)
    nombre = models.CharField(max_length=50)
    cvv = models.CharField(max_length=3)
    fecha_expiracion = models.CharField(max_length=5)
    credito = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.numero_display()

    def numero_display(self):
        return '-'.join(re.findall(r'\d{4}', str(self.numero)))

    def numero_cifrado_display(self):
        return f'****-****-****-{str(self.numero)[-4:]}'

    @property
    def vigente(self):
        exp_mes, exp_anio = self.fecha_expiracion.split('/')
        exp = f'20{exp_anio}-{exp_mes}'
        hoy = date.today()
        mes = f'{hoy.year}-{f"0{hoy.month}"[-2:]}'
        return mes <= exp

    @property
    def monto_usado(self):
        return self.transacciones.aggregate(total=Sum(
            Case(When(estado=Transaccion.Estados.FINALIZADA, then='monto'), default=0),
        ))['total'] or 0

    @property
    def saldo_restante(self):
        return self.credito - self.monto_usado

    def can_pago(self, monto):
        if Data.BLOQUEO:
            return Err('El sistema se encuentra bloqueado')
        if not self.vigente:
            return Err('La tarjeta está vencida')
        if self.saldo_restante < monto:
            return Err('Saldo insuficiente')
        return Ok()

    def pagar_tarjeta(self, monto):
        self.transacciones.create(monto=-monto, detalle='Pago tarjeta', estado=Transaccion.Estados.FINALIZADA)


class Transaccion(models.Model):
    class Estados(models.TextChoices):
        PENDIENTE = 'P', 'Pendiente'
        FINALIZADA = 'F', 'Finalizada'
        RECHAZADA = 'R', 'Rechazada'
        EXPIRADA = 'E', 'Expirada'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tarjeta = models.ForeignKey(Tarjeta, on_delete=models.CASCADE, null=True, related_name='transacciones')
    monto = models.IntegerField()
    detalle = models.CharField(max_length=500)
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_pago = models.DateTimeField(null=True)
    estado = models.CharField(choices=Estados.choices, max_length=1)
    success_url = models.URLField()
    error_url = models.URLField()
    redireccion_url = models.URLField()

    class Meta:
        ordering = ['-fecha']

    @property
    def fecha_expiracion(self):
        return self.fecha + timedelta(seconds=Data.TIEMPO_TRANSACCION)

    @property
    def segundos_restantes(self):
        if self.estado != Transaccion.Estados.PENDIENTE:
            return 0
        return int((self.fecha_expiracion - datetime.now(tz=timezone.utc)).total_seconds())

    def pago_tarjeta(self, tarjeta):
        self.tarjeta = tarjeta
        self.detalle = 'Pago tarjeta'
        self.estado = Transaccion.Estados.FINALIZADA
        self.save()

    def get_expirado(self, update=True, notifica=True):
        if self.estado == Transaccion.Estados.EXPIRADA:
            return True
        if self.estado != Transaccion.Estados.PENDIENTE:
            return False
        expirado = self.segundos_restantes <= 0
        if update and expirado:
            self.estado = Transaccion.Estados.EXPIRADA
            self.save()
            if notifica and self.error_url:
                make_request(self.error_url)
        return expirado

    def set_pagado(self, tarjeta, notifica=True):
        self.tarjeta = tarjeta
        self.estado = Transaccion.Estados.FINALIZADA
        self.fecha_pago = datetime.now(tz=timezone.utc)
        self.save()
        if notifica and self.success_url:
            make_request(self.success_url)

    @staticmethod
    def crear_transaccion_pendiente(monto, detalle, success_url, error_url, redireccion_url):
        transaccion = Transaccion.objects.create(
            tarjeta=None,
            monto=monto,
            detalle=detalle,
            estado=Transaccion.Estados.PENDIENTE,
            success_url=success_url,
            error_url=error_url,
            redireccion_url=redireccion_url,
        )
        call_func_with_delay(transaccion.get_expirado, Data.TIEMPO_TRANSACCION)
        return transaccion
