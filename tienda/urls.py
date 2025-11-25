from django.urls import path
from . import views
from .views import producto_detalle

app_name = 'tienda'

urlpatterns = [
    path('', views.inicio, name='inicio'),

    # Auth
    path('registro/', views.registro, name='registro'),
    path('login/', views.IniciarSesionView.as_view(), name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    path('perfil/', views.perfil, name='perfil'),

    # Carrito
    path('carrito/', views.carrito_ver, name='carrito_ver'),
    path('carrito/agregar/<int:producto_id>/', views.carrito_agregar, name='carrito_agregar'),
    path('carrito/set/<int:producto_id>/', views.carrito_set, name='carrito_set'),
    path('carrito/eliminar/<int:producto_id>/', views.carrito_eliminar, name='carrito_eliminar'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('pedido-exito/<int:pedido_id>/', views.pedido_exito, name='pedido_exito'),
    
    # ===== PANEL (solo staff) =====
    path('panel/', views.panel_home, name='panel_home'),

    # Productos (CRUD)
    path("panel/productos/", views.panel_productos, name="panel_productos"),
    path("panel/productos/nuevo/", views.panel_producto_nuevo, name="panel_producto_nuevo"),
    path("panel/productos/<int:pk>/editar/", views.panel_producto_editar, name="panel_producto_editar"),
    path("panel/productos/<int:pk>/eliminar/", views.panel_producto_eliminar, name="panel_producto_eliminar"),
    path("panel/productos/<int:pk>/desactivar/", views.panel_producto_desactivar, name="panel_producto_desactivar"),

    # Pedidos
    path("panel/pedidos/", views.panel_pedidos, name="panel_pedidos"),
    path("panel/pedidos/<int:pk>/", views.panel_pedido_detalle, name="panel_pedido_detalle"),

    # Ficha de producto
    path('producto/<int:pk>/', producto_detalle, name='producto_detalle'),

]
