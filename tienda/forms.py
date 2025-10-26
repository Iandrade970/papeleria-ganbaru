# tienda/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Producto, Pedido

class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", required=False)
    last_name = forms.CharField(label="Apellido", required=False)
    email = forms.EmailField(label="Email", required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ["nombre", "descripcion", "resumen", "precio", "stock", "disponible", "categoria"]  # o "categoria"
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }


class PedidoEstadoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["estado", "descuento"]
