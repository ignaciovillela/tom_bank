# Generated by Django 4.2 on 2023-04-24 14:46

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tarjeta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.IntegerField(auto_created=True, unique=True)),
                ('nombre', models.CharField(max_length=50)),
                ('cvv', models.CharField(max_length=3)),
                ('fecha_expiracion', models.CharField(max_length=5)),
                ('credito', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Transaccion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('monto', models.IntegerField()),
                ('detalle', models.CharField(max_length=500)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('fecha_pago', models.DateTimeField(null=True)),
                ('estado', models.CharField(choices=[('P', 'Pendiente'), ('F', 'Finalizada'), ('R', 'Rechazada'), ('E', 'Expirada')], max_length=1)),
                ('success_url', models.URLField()),
                ('error_url', models.URLField()),
                ('redireccion_url', models.URLField()),
                ('tarjeta', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transacciones', to='tom.tarjeta')),
            ],
            options={
                'ordering': ['-fecha'],
            },
        ),
    ]
