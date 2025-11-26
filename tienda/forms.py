# tienda/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Producto, Categoria, Pedido, Descuento

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

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "imagen"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
        }


class DescuentoForm(forms.ModelForm):
    class Meta:
        model = Descuento
        fields = ["codigo", "porcentaje", "activo"]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "porcentaje": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 90}),
        }
