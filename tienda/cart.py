from decimal import Decimal
from .models import Producto

CART_SESSION_KEY = 'cart'

class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(CART_SESSION_KEY, {})

    def save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True

    def add(self, product_id, qty=1):
        pid = str(product_id)
        self.cart[pid] = self.cart.get(pid, 0) + int(qty)
        if self.cart[pid] <= 0:
            self.cart.pop(pid, None)
        self.save()

    def set(self, product_id, qty):
        pid = str(product_id)
        if int(qty) <= 0:
            self.cart.pop(pid, None)
        else:
            self.cart[pid] = int(qty)
        self.save()

    def remove(self, product_id):
        self.cart.pop(str(product_id), None)
        self.save()

    def clear(self):
        self.session.pop(CART_SESSION_KEY, None)
        self.session.modified = True

    # utilidades de lectura
    def items(self):
        '''
        Genera items enriquecidos con objeto Producto y subtotales.
        '''
        pids = [int(pid) for pid in self.cart.keys()]
        productos = {p.id: p for p in Producto.objects.filter(id__in=pids, disponible=True)}
        for pid, qty in self.cart.items():
            prod = productos.get(int(pid))
            if not prod:
                continue
            subtotal = Decimal(qty) * prod.precio
            yield {
                'producto': prod,
                'cantidad': qty,
                'precio_unitario': prod.precio,
                'subtotal': subtotal,
            }

    def total(self):
        return sum(item['subtotal'] for item in self.items())
