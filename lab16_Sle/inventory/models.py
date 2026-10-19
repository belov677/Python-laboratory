"""Модели предметной области «Склад» (вариант 17)."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models, transaction
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone


class Warehouse(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    city = models.CharField("Город", max_length=100)
    address = models.CharField("Адрес", max_length=200)

    class Meta:
        verbose_name = "склад"
        verbose_name_plural = "склады"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.city})"


class Supplier(models.Model):
    name = models.CharField("Название", max_length=150)
    inn = models.CharField("ИНН", max_length=12, unique=True,
                           validators=[RegexValidator(r"^\d{10}(\d{2})?$", "ИНН — 10 или 12 цифр")])
    email = models.EmailField("Email")
    phone = models.CharField("Телефон", max_length=30, blank=True)
    city = models.CharField("Город", max_length=100)

    class Meta:
        verbose_name = "поставщик"
        verbose_name_plural = "поставщики"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("supplier_detail", args=[self.pk])


class ProductQuerySet(models.QuerySet):
    def with_stock(self):
        """Добавляет поле total — суммарный остаток по всем складам."""
        return self.annotate(total=Coalesce(Sum("stock_items__quantity"), 0))

    def critical(self):
        """Товары, суммарный остаток которых ниже минимального."""
        return self.with_stock().filter(total__lt=F("min_stock"))


class Product(models.Model):
    class Category(models.TextChoices):
        ELECTRONICS = "electronics", "Электроника"
        FOOD = "food", "Продукты"
        BUILDING = "building", "Стройматериалы"
        CLOTHES = "clothes", "Одежда"
        OFFICE = "office", "Канцелярия"

    class Unit(models.TextChoices):
        PCS = "шт", "шт"
        KG = "кг", "кг"
        L = "л", "л"
        M = "м", "м"

    sku = models.CharField("Артикул", max_length=20, unique=True,
                           validators=[RegexValidator(r"^[A-Z]{2,4}-\d{3,6}$",
                                                      "Формат артикула: ABC-123")])
    name = models.CharField("Наименование", max_length=150)
    category = models.CharField("Категория", max_length=20, choices=Category.choices)
    unit = models.CharField("Ед. изм.", max_length=5, choices=Unit.choices, default=Unit.PCS)
    price = models.DecimalField("Цена, руб.", max_digits=12, decimal_places=2,
                                validators=[MinValueValidator(Decimal("0.01"))])
    min_stock = models.PositiveIntegerField("Минимальный остаток", default=10)
    description = models.TextField("Описание", blank=True)
    suppliers = models.ManyToManyField(Supplier, related_name="products", blank=True,
                                       verbose_name="Поставщики")
    warehouses = models.ManyToManyField(Warehouse, through="StockItem", related_name="products",
                                        verbose_name="Склады")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ["name"]

    def __str__(self):
        return f"{self.sku} {self.name}"

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.pk])

    def clean(self):
        if self.name and self.name.strip().lower() == "товар":
            raise ValidationError({"name": "Укажите конкретное наименование товара"})

    @property
    def total_stock(self) -> int:
        if hasattr(self, "total"):
            return self.total
        return self.stock_items.aggregate(t=Coalesce(Sum("quantity"), 0))["t"]

    @property
    def is_critical(self) -> bool:
        return self.total_stock < self.min_stock


class StockItem(models.Model):
    """Остаток товара на конкретном складе (промежуточная модель M2M)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_items",
                                verbose_name="Товар")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stock_items",
                                  verbose_name="Склад")
    quantity = models.PositiveIntegerField("Количество", default=0)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "остаток"
        verbose_name_plural = "остатки"
        constraints = [models.UniqueConstraint(fields=["product", "warehouse"],
                                               name="unique_product_warehouse")]
        ordering = ["product__name", "warehouse__name"]

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class Shipment(models.Model):
    """Поставка товара от поставщика на склад."""
    class Status(models.TextChoices):
        PLANNED = "planned", "Ожидается"
        RECEIVED = "received", "Принята"
        CANCELLED = "cancelled", "Отменена"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="shipments",
                                verbose_name="Товар")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="shipments",
                                 verbose_name="Поставщик")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="shipments",
                                  verbose_name="Склад")
    quantity = models.PositiveIntegerField("Количество", validators=[MinValueValidator(1)])
    purchase_price = models.DecimalField("Закупочная цена", max_digits=12, decimal_places=2,
                                         validators=[MinValueValidator(Decimal("0.01"))])
    status = models.CharField("Статус", max_length=10, choices=Status.choices,
                              default=Status.PLANNED)
    expected_date = models.DateField("Ожидаемая дата", default=timezone.localdate)
    received_at = models.DateTimeField("Принята", null=True, blank=True)

    class Meta:
        verbose_name = "поставка"
        verbose_name_plural = "поставки"
        ordering = ["-expected_date", "-id"]

    def __str__(self):
        return f"Поставка №{self.pk}: {self.product.name} × {self.quantity}"

    @property
    def total(self) -> Decimal:
        return self.purchase_price * self.quantity

    def clean(self):
        if self.product_id and self.supplier_id and \
                not self.product.suppliers.filter(pk=self.supplier_id).exists():
            raise ValidationError({"supplier": "Этот поставщик не поставляет выбранный товар"})

    @transaction.atomic
    def receive(self) -> StockItem:
        """Приём поставки: статус «принята» и увеличение остатка на складе."""
        if self.status != self.Status.PLANNED:
            raise ValidationError("Принять можно только ожидаемую поставку")
        item, _ = StockItem.objects.select_for_update().get_or_create(
            product=self.product, warehouse=self.warehouse)
        item.quantity = F("quantity") + self.quantity
        item.save()
        self.status = self.Status.RECEIVED
        self.received_at = timezone.now()
        self.save()
        item.refresh_from_db()
        return item
