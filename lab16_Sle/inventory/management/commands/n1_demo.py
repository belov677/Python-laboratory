"""Демонстрация проблемы N+1 и её устранения: python manage.py n1_demo"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import CaptureQueriesContext

from inventory.models import Product, StockItem


class Command(BaseCommand):
    help = "Сравнивает количество SQL-запросов без и с select_related/prefetch_related"

    def run(self, title, func):
        with CaptureQueriesContext(connection) as ctx:
            lines = func()
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title}"))
        self.stdout.write(f"  строк выведено: {lines}, SQL-запросов: {len(ctx.captured_queries)}")
        for q in ctx.captured_queries[:3]:
            self.stdout.write(f"    {q['sql'][:110]}…")
        if len(ctx.captured_queries) > 3:
            self.stdout.write(f"    … ещё {len(ctx.captured_queries) - 3} запросов")
        return len(ctx.captured_queries)

    def handle(self, *args, **options):
        def bad_stock():
            return len([f"{i.product.name} {i.warehouse.name}" for i in StockItem.objects.all()])

        def good_stock():
            return len([f"{i.product.name} {i.warehouse.name}"
                        for i in StockItem.objects.select_related("product", "warehouse")])

        def bad_m2m():
            return len([[s.name for s in p.suppliers.all()] for p in Product.objects.all()])

        def good_m2m():
            return len([[s.name for s in p.suppliers.all()]
                        for p in Product.objects.prefetch_related("suppliers")])

        a = self.run("1. ПЛОХО: StockItem.objects.all() + обращение к product и warehouse", bad_stock)
        b = self.run("2. ХОРОШО: select_related('product', 'warehouse') — JOIN", good_stock)
        c = self.run("3. ПЛОХО: Product.objects.all() + p.suppliers.all() (M2M)", bad_m2m)
        d = self.run("4. ХОРОШО: prefetch_related('suppliers') — 2 запроса", good_m2m)
        self.stdout.write(self.style.SUCCESS(f"\nИтого: {a} → {b} запросов (FK), {c} → {d} (M2M)"))
