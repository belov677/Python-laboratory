from django.contrib import admin
from django.db.models import F

from .models import Product, Shipment, StockItem, Supplier, Warehouse


class StockInline(admin.TabularInline):
    model = StockItem
    extra = 0


class CriticalFilter(admin.SimpleListFilter):
    title = "остаток"
    parameter_name = "stock"

    def lookups(self, request, model_admin):
        return [("critical", "критический"), ("ok", "в норме")]

    def queryset(self, request, queryset):
        if self.value() == "critical":
            return queryset.filter(total__lt=F("min_stock"))
        if self.value() == "ok":
            return queryset.filter(total__gte=F("min_stock"))
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Расширенная настройка: вычисляемый остаток, собственный фильтр, inline, действие."""
    list_display = ("sku", "name", "category", "price", "min_stock", "total_stock_display",
                    "critical_display")
    list_display_links = ("sku", "name")
    list_editable = ("price", "min_stock")
    search_fields = ("sku", "name", "suppliers__name")
    list_filter = ("category", "unit", CriticalFilter, "suppliers")
    ordering = ("name",)
    filter_horizontal = ("suppliers",)
    inlines = [StockInline]
    list_per_page = 10
    actions = ["raise_min_stock"]
    fieldsets = (("Основное", {"fields": ("sku", "name", "category", "unit", "description")}),
                 ("Цена и запас", {"fields": ("price", "min_stock")}),
                 ("Поставщики", {"fields": ("suppliers",)}))

    def get_queryset(self, request):
        return super().get_queryset(request).with_stock()

    @admin.display(description="Остаток", ordering="total")
    def total_stock_display(self, obj):
        return obj.total

    @admin.display(description="Критический", boolean=True)
    def critical_display(self, obj):
        return obj.total < obj.min_stock

    @admin.action(description="Увеличить минимальный остаток на 10")
    def raise_min_stock(self, request, queryset):
        updated = Product.objects.filter(pk__in=queryset.values("pk")).update(
            min_stock=F("min_stock") + 10)
        self.message_user(request, f"Обновлено товаров: {updated}")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "inn", "email", "phone", "city")
    search_fields = ("name", "inn", "email")
    list_filter = ("city",)
    ordering = ("name",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "address")
    search_fields = ("name", "city")
    ordering = ("name",)


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "updated_at")
    search_fields = ("product__name", "product__sku")
    list_filter = ("warehouse",)
    ordering = ("product__name",)
    list_select_related = ("product", "warehouse")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "supplier", "warehouse", "quantity", "purchase_price",
                    "status", "expected_date")
    search_fields = ("product__name", "supplier__name")
    list_filter = ("status", "warehouse", "supplier")
    ordering = ("-expected_date",)
    date_hierarchy = "expected_date"
    list_select_related = ("product", "supplier", "warehouse")
