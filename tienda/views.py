# tienda/views.py
import secrets
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import Http404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Max

from .cart import Cart
from .forms import RegistroForm, ProductoForm, PedidoEstadoForm
from .models import Producto, Categoria, Pedido, DetallePedido, Descuento


# --------- HOME / CATÁLOGO ----------
def inicio(request):
    qs = Producto.objects.all()
    categorias = Categoria.objects.all()

    # GET params
    q        = request.GET.get("q", "").strip()
    cat_slug = request.GET.get("cat", "").strip()
    solo_ok  = request.GET.get("ok") == "1"
    pmin     = request.GET.get("pmin", "").strip()
    pmax     = request.GET.get("pmax", "").strip()
    ordenar  = request.GET.get("ord", "recientes")

    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))

    # ⚠️ IMPORTANTE: si tu FK en Producto se llama 'Categoria' (con C mayúscula),
    # el filtro correcto es 'Categoria__slug', no 'categoria__slug'.
    # Si tu FK se llama 'categoria' (minúscula), deja 'categoria__slug'.
    if cat_slug:
        try:
            qs = qs.filter(categoria__slug=cat_slug)  # usa Categoria__slug si tu campo es 'Categoria'
        except Exception:
            qs = qs.filter(Categoria__slug=cat_slug)

    if solo_ok:
        qs = qs.filter(disponible=True)

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

    orden_map = {
        "recientes": "-creado",
        "precio_asc": "precio",
        "precio_desc": "-precio",
        "nombre_asc": "nombre",
        "nombre_desc": "-nombre",
    }
    qs = qs.order_by(orden_map.get(ordenar, "-creado"))

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
    try:
        producto = Producto.objects.get(id=producto_id)
    except Producto.DoesNotExist:
        messages.error(request, "Este producto no existe.")
        return redirect("tienda:inicio")

    if not producto.disponible:
        messages.error(request, "No se puede agregar al carrito: el producto no está disponible.")
        # Redirigimos a donde estaba el usuario
        next_url = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")
        if not next_url:
            next_url = reverse("tienda:inicio")
        return redirect(next_url)

    qty = int(request.POST.get("qty", 1)) if request.method == "POST" else 1

    Cart(request).add(producto.id, qty)
    messages.success(request, f"Agregado: {producto.nombre}")

    next_url = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")
    if not next_url:
        next_url = reverse("tienda:carrito_ver")

    return redirect(next_url)


def carrito_set(request, producto_id):
    if request.method == "POST":
        qty = int(request.POST.get("qty", 1))
        Cart(request).set(producto_id, qty)
    return redirect("tienda:carrito_ver")

def carrito_eliminar(request, producto_id):
    Cart(request).remove(producto_id)
    return redirect("tienda:carrito_ver")


# --------- CHECKOUT ----------
@login_required
def checkout(request):
    cart = Cart(request)
    items = list(cart.items())
    if not items:
        messages.info(request, "Tu carrito está vacío.")
        return redirect("tienda:carrito_ver")

    if request.method == "GET":
        token = secrets.token_urlsafe(8)
        request.session["checkout_token"] = token
        return render(request, "tienda/checkout.html", {"items": items, "total": cart.total(), "token": token})

    posted = request.POST.get("token")
    saved = request.session.get("checkout_token")
    if not posted or posted != saved:
        messages.warning(request, "La orden ya fue procesada o tu sesión caducó.")
        return redirect("tienda:carrito_ver")
    request.session.pop("checkout_token", None)

    codigo_desc = request.POST.get("cupon", "").strip()
    cupon = Descuento.objects.filter(codigo=codigo_desc, activo=True).first() if codigo_desc else None

    with transaction.atomic():
        ids = [it["producto"].id for it in items]
        productos_bloqueados = Producto.objects.select_for_update().filter(id__in=ids).in_bulk()

        for it in items:
            p = productos_bloqueados[it["producto"].id]
            if p.stock < it["cantidad"]:
                messages.error(request, f"No hay stock suficiente de '{p.nombre}'. Disponible: {p.stock}.")
                return redirect("tienda:carrito_ver")

        ultimo_num = (
        Pedido.objects
            .filter(usuario=request.user)
            .aggregate(Max("numero_usuario"))["numero_usuario__max"]
        or 0
        )

        pedido = Pedido.objects.create(usuario=request.user, descuento=cupon, estado="PENDIENTE",numero_usuario=ultimo_num + 1,)

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


# =======================
# ===== PANEL STAFF =====
# =======================

@staff_member_required
def panel_home(request):
    total_prod = Producto.objects.count()
    total_ped = Pedido.objects.count()
    pendientes = Pedido.objects.filter(estado="PENDIENTE").count()
    return render(request, "tienda/panel/home.html", {
        "total_prod": total_prod, "total_ped": total_ped, "pendientes": pendientes,
    })

@staff_member_required
def panel_productos(request):
    productos = Producto.objects.all().order_by("nombre")
    return render(request, "tienda/panel/productos_list.html", {"productos": productos})

@staff_member_required
def panel_producto_nuevo(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado.")
            return redirect("tienda:panel_productos")
    else:
        form = ProductoForm()
    return render(request, "tienda/panel/producto_form.html", {"form": form, "titulo": "Nuevo producto"})

@staff_member_required
def panel_producto_editar(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=p)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado.")
            return redirect("tienda:panel_productos")
    else:
        form = ProductoForm(instance=p)
    return render(request, "tienda/panel/producto_form.html", {"form": form, "titulo": f"Editar: {p.nombre}"})

@staff_member_required
def panel_producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        try:
            producto.delete()
            messages.success(request, "Producto eliminado correctamente.")
        except ProtectedError:
            messages.error(
                request,
                "No puedes eliminar este producto porque ya tiene pedidos asociados. "
                "Desactívalo si deseas que no se siga vendiendo."
            )
        return redirect("tienda:panel_productos")

    # Página de confirmación (opcional)
    return render(request, "tienda/panel/producto_eliminar.html", {"producto": producto})

@staff_member_required
def panel_pedidos(request):
    pedidos = Pedido.objects.select_related("usuario", "descuento").order_by("-creado")
    return render(request, "tienda/panel/pedidos_list.html", {"pedidos": pedidos})

@staff_member_required
def panel_producto_desactivar(request, pk):
    """
    Desactiva el producto (disponible=False) para que no aparezca en el catálogo.
    """
    p = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        p.disponible = False
        p.save()
        messages.success(
            request,
            f"El producto «{p.nombre}» fue desactivado. Ya no aparecerá en el catálogo."
        )
        return redirect("tienda:panel_productos")

    # si quieres confirmación, puedes usar el mismo template de eliminar:
    return render(request, "tienda/panel/producto_desactivar.html", {"producto": p})

@staff_member_required
def panel_pedido_detalle(request, pk):
    ped = get_object_or_404(Pedido.objects.prefetch_related("detalles__producto"), pk=pk)
    if request.method == "POST":
        form = PedidoEstadoForm(request.POST, instance=ped)
        if form.is_valid():
            form.save()
            messages.success(request, "Pedido actualizado.")
            return redirect("tienda:panel_pedido_detalle", pk=pk)
    else:
        form = PedidoEstadoForm(instance=ped)
    return render(request, "tienda/panel/pedido_detalle.html", {"pedido": ped, "form": form})


def producto_detalle(request, pk):
    try:
        p = Producto.objects.get(pk=pk)
    except Producto.DoesNotExist:
        # Si de verdad no existe, 404 normal
        raise Http404("Producto no encontrado")

    if not p.disponible:
        messages.error(request, "Este producto no está disponible por el momento.")
        return redirect("tienda:inicio")

    return render(request, "tienda/producto_detalle.html", {"p": p})

