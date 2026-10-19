from django import forms

from .models import Product, Shipment, StockItem, Supplier


class StyledMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.setdefault("class", "input")


class ProductForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "category", "unit", "price", "min_stock", "suppliers",
                  "description"]
        widgets = {"suppliers": forms.CheckboxSelectMultiple,
                   "description": forms.Textarea(attrs={"rows": 3})}

    def clean_sku(self):
        return self.cleaned_data["sku"].strip().upper()

    def clean(self):
        data = super().clean()
        if data.get("category") == Product.Category.FOOD and data.get("unit") == Product.Unit.M:
            self.add_error("unit", "Для продуктов нельзя использовать единицу «м»")
        return data


class SupplierForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "inn", "email", "phone", "city"]


class ShipmentForm(StyledMixin, forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ["product", "supplier", "warehouse", "quantity", "purchase_price", "expected_date"]
        widgets = {"expected_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}


class StockForm(StyledMixin, forms.ModelForm):
    """Корректировка остатка (инвентаризация)."""
    class Meta:
        model = StockItem
        fields = ["quantity"]


class ProductFilterForm(forms.Form):
    SORTS = [("name", "Название А→Я"), ("-name", "Название Я→А"), ("price", "Цена ↑"),
             ("-price", "Цена ↓"), ("total", "Остаток ↑"), ("-total", "Остаток ↓")]
    q = forms.CharField(required=False, label="Поиск")
    category = forms.ChoiceField(required=False, label="Категория",
                                 choices=[("", "Все категории")] + Product.Category.choices)
    supplier = forms.ModelChoiceField(required=False, label="Поставщик",
                                      queryset=Supplier.objects.all(), empty_label="Все поставщики")
    critical = forms.BooleanField(required=False, label="Только критические")
    sort = forms.ChoiceField(required=False, choices=SORTS, label="Сортировка")
