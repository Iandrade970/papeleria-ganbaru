# tienda/views.py
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
import secrets
from decimal import Decimal, InvalidOperation
from django.db.models import Q
from .models import Producto, Categoria

from .models import Producto, Pedido, DetallePedido, Descuento
from .forms import RegistroForm
from .cart import Cart
from .models import Producto, Categoria


# --------- HOME / CATÁLOGO ----------
def inicio(request):
    qs = Producto.objects.all()
    categorias = Categoria.objects.all()

    # --- leer parámetros GET ---
    q        = request.GET.get("q", "").strip()
    cat_slug = request.GET.get("cat", "").strip()
    solo_ok  = request.GET.get("ok") == "1"
    pmin     = request.GET.get("pmin", "").strip()
    pmax     = request.GET.get("pmax", "").strip()
    ordenar  = request.GET.get("ord", "recientes")

    # --- aplicar filtros ---
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    if cat_slug:
        qs = qs.filter(categoria__slug=cat_slug)
    if solo_ok:
        qs = qs.filter(disponible=True)

    # rango de precios
    def as_decimal(v):
        try:
            return Decimal(v.replace(",", ".")) if v else None
        except (InvalidOperation, AttributeError):
            return None
    dmin, dmax = as_decimal(pmin), as_decimal(pmax)
    if dmin is not None:
        qs = qs.filter(precio__gte=dmin)
    if dmax is not None:
        qs = qs.filter(precio__lte=dmax)

    # ordenar
    orden_map = {
        "recientes": "-creado",
        "precio_asc": "precio",
        "precio_desc": "-precio",
        "nombre_asc": "nombre",
        "nombre_desc": "-nombre",
    }
    qs = qs.order_by(orden_map.get(ordenar, "-creado"))

    # --- enviar todo al template ---
    ctx = {
        "productos": qs,
        "categorias": categorias,
        "cat_seleccionada": cat_slug,
        "f": {"q": q, "ok": solo_ok, "pmin": pmin, "pmax": pmax, "ord": ordenar},
    }
    return render(request, "tienda/index.html", ctx)



# --------- AUTH ----------
class IniciarSesionView(LoginView):
    template_name = "registration/login.html"

def cerrar_sesion(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "Has cerrado sesión.")
        return redirect("tienda:inicio")
    return render(request, "registration/logout_confirm.html")

def registro(request):
    if request.user.is_authenticated:
        return redirect("tienda:inicio")
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"¡Bienvenido/a, {user.first_name or user.username}!")
            return redirect("tienda:inicio")
    else:
        form = RegistroForm()
    return render(request, "tienda/registro.html", {"form": form})

@login_required
def perfil(request):
    pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related("detalles", "detalles__producto")
    return render(request, "tienda/perfil.html", {"pedidos": pedidos})


# --------- CARRITO ----------
def carrito_ver(request):
    cart = Cart(request)
    return render(request, "tienda/carrito.html", {"items": list(cart.items()), "total": cart.total()})

def carrito_agregar(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, disponible=True)
    qty = int(request.POST.get("qty", 1)) if request.method == "POST" else 1
    Cart(request).add(producto.id, qty)
    messages.success(request, f"Agregado: {producto.nombre}")
    return redirect("tienda:carrito_ver")

def carrito_set(request, producto_id):
    if request.method == "POST":
        qty = int(request.POST.get("qty", 1))
        Cart(request).set(producto_id, qty)
    return redirect("tienda:carrito_ver")

def carrito_eliminar(request, producto_id):
    Cart(request).remove(producto_id)
    return redirect("tienda:carrito_ver")


# --------- CHECKOUT con stock y anti-doble envío ----------
@login_required
def checkout(request):
    cart = Cart(request)
    items = list(cart.items())
    if not items:
        messages.info(request, "Tu carrito está vacío.")
        return redirect("tienda:carrito_ver")

    # GET: muestra resumen y crea token anti-doble envío
    if request.method == "GET":
        token = secrets.token_urlsafe(8)
        request.session["checkout_token"] = token
        return render(request, "tienda/checkout.html", {"items": items, "total": cart.total(), "token": token})

    # POST: valida token
    posted = request.POST.get("token")
    saved = request.session.get("checkout_token")
    if not posted or posted != saved:
        messages.warning(request, "La orden ya fue procesada o tu sesión caducó.")
        return redirect("tienda:carrito_ver")
    request.session.pop("checkout_token", None)

    codigo_desc = request.POST.get("cupon", "").strip()
    cupon = Descuento.objects.filter(codigo=codigo_desc, activo=True).first() if codigo_desc else None

    with transaction.atomic():
        # Bloquea productos y verifica stock
        ids = [it["producto"].id for it in items]
        productos_bloqueados = (
            Producto.objects.select_for_update().filter(id__in=ids).in_bulk()
        )  # dict {id: Producto}

        for it in items:
            p = productos_bloqueados[it["producto"].id]
            if p.stock < it["cantidad"]:
                messages.error(request, f"No hay stock suficiente de '{p.nombre}'. Disponible: {p.stock}.")
                return redirect("tienda:carrito_ver")

        # Crea pedido + detalles y descuenta stock
        pedido = Pedido.objects.create(usuario=request.user, descuento=cupon, estado="PENDIENTE")

        for it in items:
            p = productos_bloqueados[it["producto"].id]
            p.stock -= it["cantidad"]
            if p.stock == 0:
                p.disponible = False
            p.save()

            DetallePedido.objects.create(
                pedido=pedido,
                producto=p,
                cantidad=it["cantidad"],
                precio_unitario=it["precio_unitario"],
            )

        pedido.recomputar_total()
        pedido.save()

    cart.clear()
    messages.success(request, f"Pedido #{pedido.id} creado correctamente.")
    return redirect(reverse("tienda:pedido_exito", args=[pedido.id]))


def pedido_exito(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, "tienda/pedido_exito.html", {"pedido": pedido})
