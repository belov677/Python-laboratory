"""Демонстрация обязательных запросов Django ORM: python manage.py orm_demo"""
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Max, Min, Sum

from inventory.models import Product, Shipment, StockItem, Supplier, Warehouse


class Command(BaseCommand):
    help = "Выполняет all/filter/exclude/get/order_by/count/exists/aggregate/annotate"

    def show(self, title, value):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n>>> {title}"))
        self.stdout.write(str(value))

    def handle(self, *args, **options):
        self.show("Warehouse.objects.all()", list(Warehouse.objects.all()))
        qs = Product.objects.filter(category="electronics", price__gte=1000)
        self.show("filter(category='electronics', price__gte=1000)",
                  "\n".join(f"  {p.sku} {p.name} — {p.price}" for p in qs))
        self.show("SQL этого QuerySet", qs.query)
        self.show("exclude(category__in=['food', 'building']).count()",
                  Product.objects.exclude(category__in=["food", "building"]).count())
        p = Product.objects.get(sku="EL-1001")
        self.show("get(sku='EL-1001')", f"{p} | цена {p.price} | остаток {p.total_stock}")
        try:
            Product.objects.get(sku="NO-0000")
        except Product.DoesNotExist as error:
            self.show("get(sku='NO-0000')", f"Product.DoesNotExist: {error}")
        self.show("order_by('-price')[:3]",
                  "\n".join(f"  {p.name} — {p.price}" for p in Product.objects.order_by("-price")[:3]))
        self.show("count()", f"товаров: {Product.objects.count()}, остатков: {StockItem.objects.count()}")
        self.show("filter(quantity=0).exists()", StockItem.objects.filter(quantity=0).exists())
        self.show("aggregate(Avg, Min, Max, Sum)",
                  Product.objects.aggregate(avg=Avg("price"), min=Min("price"), max=Max("price"),
                                            stock=Sum("stock_items__quantity")))
        rows = (Supplier.objects.annotate(products_n=Count("products", distinct=True),
                                          shipments_n=Count("shipments", distinct=True))
                .order_by("-products_n"))
        self.show("annotate(Count) по поставщикам",
                  "\n".join(f"  {s.name:22} товаров: {s.products_n}, поставок: {s.shipments_n}"
                            for s in rows))
        self.show("Связанные объекты: товар → поставщики (M2M) → склады (through StockItem)",
                  f"  {p.name}: поставщики {[s.name for s in p.suppliers.all()]}, "
                  f"склады {[w.name for w in p.warehouses.all()]}")
        w = Warehouse.objects.get(name="Центральный")
        self.show("Обратная связь warehouse.stock_items (первые 3)",
                  "\n".join(f"  {i.product.name}: {i.quantity}"
                            for i in w.stock_items.select_related("product")[:3]))
        self.show("Критические остатки (annotate + F)",
                  "\n".join(f"  {p.sku} {p.name:30} остаток {p.total:5} < мин. {p.min_stock}"
                            for p in Product.objects.critical().order_by("total")))
        self.show("values('status').annotate(n=Count('id'))",
                  list(Shipment.objects.values("status").annotate(n=Count("id")).order_by("status")))
