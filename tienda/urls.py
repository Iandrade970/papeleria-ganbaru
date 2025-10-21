from django.urls import path
from . import views

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
]
