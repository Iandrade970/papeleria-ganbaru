from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.utils.html import format_html
from .models import Producto, Pedido, DetallePedido, Descuento, Categoria

# --- Categoria ---
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug")
    prepopulated_fields = {"slug": ("nombre",)}

# --- Producto ---
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("thumb", "nombre", "precio", "stock", "disponible", "categoria", "creado")
    list_filter = ("disponible", "categoria")
    search_fields = ("nombre", "descripcion")
    fields = ("nombre", "descripcion", "resumen", "precio", "stock", "disponible", "categoria", "imagen")

    def thumb(self, obj):
        if getattr(obj, "imagen", None):
            return format_html('<img src="{}" style="height:40px;border-radius:6px"/>', obj.imagen.url)
        return "—"
    thumb.short_description = "Imagen"

# Asegura que no esté registrado previamente y regístralo UNA sola vez
try:
    admin.site.unregister(Producto)
except NotRegistered:
    pass
admin.site.register(Producto, ProductoAdmin)

# --- Pedido + detalle inline ---
class DetalleInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ("precio_unitario",)
    fields = ("producto", "cantidad", "precio_unitario")

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "estado", "creado", "total")
    list_filter = ("estado", "creado")
    search_fields = ("id", "usuario__username")
    readonly_fields = ("total",)
    fields = ("usuario", "estado", "descuento", "total")
    inlines = [DetalleInline]

# --- Descuento ---
@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "porcentaje", "activo", "creado")
    list_filter = ("activo",)
    search_fields = ("codigo",)
