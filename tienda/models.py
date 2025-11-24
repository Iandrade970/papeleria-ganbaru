from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F, Sum, DecimalField
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.humanize.templatetags.humanize import intcomma



# ----------------- CATEGORÍA -----------------
class Categoria(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    imagen = models.ImageField(upload_to="categorias/", null=True, blank=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


# ----------------- PRODUCTO -----------------
class Producto(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to="productos/", null=True, blank=True)
    precio = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    def precio_formateado(self):
        """Devuelve el precio sin decimales y con separador de miles (p. ej. $ 12.000)."""
        try:
            return f"$ {intcomma(int(self.precio))}"
        except Exception:
            return f"$ {self.precio}"

    

    resumen = models.CharField(
        "resumen corto (para la tarjeta)",
        max_length=160,
        blank=True,
        help_text="Texto breve que se mostrará en el catálogo (máx. 160 caracteres)."
    )
    disponible = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    # FK correcta (minúsculas) y después de declarar Categoria:
    categoria = models.ForeignKey(
        Categoria, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="productos"
    )

    class Meta:
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["disponible", "stock"]),
            models.Index(fields=["nombre"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(precio__gte=0), name="producto_precio_no_negativo"),
            models.CheckConstraint(check=Q(stock__gte=0),  name="producto_stock_no_negativo"),
        ]

    def clean(self):
        # si no hay stock, fuerzo no disponible
        if self.stock == 0 and self.disponible:
            self.disponible = False

    def __str__(self):
        return f"{self.nombre} (${self.precio}) · stock:{self.stock}"


# ----------------- DESCUENTO / CUPÓN -----------------
class Descuento(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    porcentaje = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.codigo} (-{self.porcentaje}%)"


# ----------------- PEDIDO -----------------
class Pedido(models.Model):
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("PAGADO", "Pagado"),
        ("ENVIADO", "Enviado"),
        ("CANCELADO", "Cancelado"),
    ]
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos"
    )
    descuento = models.ForeignKey(Descuento, null=True, blank=True, on_delete=models.SET_NULL)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="PENDIENTE")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado = models.DateTimeField(default=timezone.now)

    def total_formateado(self):
        try:
            return f"$ {intcomma(int(self.total))}"
        except Exception:
            return f"$ {self.total}"

    class Meta:
        ordering = ["-creado"]
        indexes = [models.Index(fields=["estado", "creado"])]

    def recomputar_total(self):
        subtotal = self.detalles.aggregate(
            s=Sum(F("precio_unitario") * F("cantidad"), output_field=DecimalField(max_digits=12, decimal_places=2))
        )["s"] or Decimal("0.00")
        if self.descuento and self.descuento.activo:
            subtotal = subtotal * (Decimal("100") - Decimal(self.descuento.porcentaje)) / Decimal("100")
        self.total = subtotal.quantize(Decimal("0.01"))
        return self.total

    def __str__(self):
        return f"Pedido #{self.id} · {self.usuario} · {self.estado}"


# ----------------- DETALLE DE PEDIDO -----------------
class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name="detalles", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    def precio_unitario_formateado(self):
        try:
            return f"$ {intcomma(int(self.precio_unitario))}"
        except Exception:
            return f"$ {self.precio_unitario}"

    def subtotal_formateado(self):
        try:
            return f"$ {intcomma(int(self.subtotal))}"
        except Exception:
            return f"$ {self.subtotal}"

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["pedido", "producto"], name="uniq_pedido_producto"),
            models.CheckConstraint(check=Q(cantidad__gt=0),         name="detalle_cant_positiva"),
            models.CheckConstraint(check=Q(precio_unitario__gte=0), name="detalle_precio_no_negativo"),
        ]

    @property
    def subtotal(self):
        return (self.precio_unitario * self.cantidad).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.cantidad} × {self.producto.nombre}"
