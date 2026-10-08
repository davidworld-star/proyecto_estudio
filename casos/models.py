from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum

class Cliente(models.Model):
    nombres = models.CharField(max_length=150)
    documento = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField()

    def __str__(self):
        return f"{self.nombres} ({self.documento})"

class EstadoCaso(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    permite_pagos = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class PerfilAbogado(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    numero_colegiatura = models.CharField(max_length=30)
    especialidad = models.CharField(max_length=100)

    def __str__(self):
        return f"Abg. {self.usuario.get_full_name() or self.usuario.username} - CAL: {self.numero_colegiatura}"

class Caso(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_inicio = models.DateField()
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='casos')
    estado = models.ForeignKey(EstadoCaso, on_delete=models.PROTECT, related_name='casos')
    abogados = models.ManyToManyField(PerfilAbogado, related_name='casos')

    def total_pagado(self):
        resultado = self.pagos.aggregate(total=Sum('monto'))
        return resultado['total'] if resultado['total'] is not None else 0

    def clean(self):
        super().clean()
        # Si el caso ya existe y tiene un estado que NO permite pagos,
        # valida que no tenga pagos registrados previamente.
        if self.pk and self.estado_id and not self.estado.permite_pagos:
            if self.pagos.exists():
                raise ValidationError(
                    f"No se puede cambiar el estado a '{self.estado.nombre}' porque el caso ya cuenta con pagos registrados."
                )

    def __str__(self):
        return f"[{self.codigo}] {self.titulo}"

class Expediente(models.Model):
    numero = models.CharField(max_length=50, unique=True)
    juzgado = models.CharField(max_length=150)
    fecha_presentacion = models.DateField()
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='expedientes')
    documento = models.FileField(upload_to='expedientes/', blank=True, null=True)

    def __str__(self):
        return f"Exp. {self.numero} - {self.juzgado}"

class Pago(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    descripcion = models.CharField(max_length=255)

    def clean(self):
        super().clean()
        # Permite la validación limpia sin bloquear la edición del Caso si no se está agregando un nuevo Pago
        if self.caso_id:
            estado_actual = getattr(self.caso, 'estado', None)
            if estado_actual and not estado_actual.permite_pagos:
                raise ValidationError(
                    f"No se pueden registrar pagos porque el estado del caso '{estado_actual.nombre}' no lo permite."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pago S/ {self.monto} - Caso: {self.caso.codigo}"