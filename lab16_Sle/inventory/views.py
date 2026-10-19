"""Представления: FBV для товаров и остатков, CBV для поставщиков и поставок."""
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ProductFilterForm, ProductForm, ShipmentForm, StockForm, SupplierForm
from .models import Product, Shipment, StockItem, Supplier, Warehouse

log = logging.getLogger("inventory")


def query_without_page(request) -> str:
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


# ---------- главная и статистика ----------
def index(request):
    context = {
        "products": Product.objects.count(),
        "suppliers": Supplier.objects.count(),
        "warehouses": Warehouse.objects.count(),
        "critical": Product.objects.critical().count(),
        "planned": Shipment.objects.filter(status=Shipment.Status.PLANNED).count(),
    }
    return render(request, "inventory/index.html", context)


@login_required
def statistics(request):
    value = ExpressionWrapper(F("quantity") * F("product__price"),
                              output_field=DecimalField(max_digits=16, decimal_places=2))
    totals = StockItem.objects.aggregate(units=Sum("quantity"), value=Sum(value))
    price = Product.objects.aggregate(avg=Avg("price"), count=Count("id"))
    by_category = (Product.objects.values("category")
                   .annotate(n=Count("id"), avg_price=Avg("price")).order_by("-n"))
    names = dict(Product.Category.choices)
    by_warehouse = (Warehouse.objects.annotate(
        positions=Count("stock_items"), units=Sum("stock_items__quantity"),
        value=Sum(F("stock_items__quantity") * F("stock_items__product__price"),
                  output_field=DecimalField(max_digits=16, decimal_places=2)))
        .order_by("-value"))
    top_supplier = (Supplier.objects
                    .annotate(received=Count("shipments",
                                             filter=Q(shipments__status=Shipment.Status.RECEIVED),
                                             distinct=True),
                              n_products=Count("products", distinct=True))
                    .order_by("-received", "name").first())
    context = {
        "count": price["count"], "avg_price": price["avg"] or 0,
        "units": totals["units"] or 0, "value": totals["value"] or 0,
        "critical": Product.objects.critical().count(),
        "no_stock": Product.objects.with_stock().filter(total=0).count(),
        "planned": Shipment.objects.filter(status=Shipment.Status.PLANNED).count(),
        "top_supplier": top_supplier,
        "by_category": [{**row, "title": names[row["category"]]} for row in by_category],
        "by_warehouse": by_warehouse,
    }
    return render(request, "inventory/statistics.html", context)


# ---------- товары (FBV) ----------
@login_required
def product_list(request):
    form = ProductFilterForm(request.GET or None)
    products = Product.objects.with_stock()
    sort = "name"
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            products = products.filter(Q(name__icontains=data["q"]) | Q(sku__icontains=data["q"]))
        if data["category"]:
            products = products.filter(category=data["category"])
        if data["supplier"]:
            products = products.filter(suppliers=data["supplier"])
        if data["critical"]:
            products = products.filter(total__lt=F("min_stock"))
        sort = data["sort"] or "name"
    products = products.order_by(sort, "id")
    page = Paginator(products, settings.PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "inventory/product_list.html",
                  {"page": page, "form": form, "query": query_without_page(request),
                   "total": page.paginator.count})


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related("suppliers"), pk=pk)
    stock = product.stock_items.select_related("warehouse")
    shipments = product.shipments.select_related("supplier", "warehouse")[:10]
    return render(request, "inventory/product_detail.html",
                  {"product": product, "stock": stock, "shipments": shipments})


@permission_required("inventory.add_product", raise_exception=True)
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        log.info("Пользователь %s создал товар %s", request.user, product.sku)
        messages.success(request, f"Товар «{product.name}» создан")
        return redirect(product)
    return render(request, "inventory/product_form.html", {"form": form, "title": "Новый товар"})


@permission_required("inventory.change_product", raise_exception=True)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        log.info("Пользователь %s изменил товар %s", request.user, product.sku)
        messages.success(request, "Изменения сохранены")
        return redirect(product)
    return render(request, "inventory/product_form.html",
                  {"form": form, "title": f"Редактирование: {product.name}", "product": product})


@permission_required("inventory.delete_product", raise_exception=True)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        log.info("Пользователь %s удалил товар %s", request.user, product.sku)
        messages.success(request, f"Товар «{product.name}» удалён")
        return redirect("product_list")
    return render(request, "inventory/product_confirm_delete.html", {"product": product})


# ---------- остатки (FBV) ----------
@login_required
def stock_list(request):
    items = StockItem.objects.select_related("product", "warehouse")
    warehouse = request.GET.get("warehouse")
    if warehouse:
        items = items.filter(warehouse_id=warehouse)
    if request.GET.get("low"):
        items = items.filter(quantity__lt=F("product__min_stock"))
    items = items.exclude(quantity__lt=0)  # демонстрация exclude()
    page = Paginator(items, settings.PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "inventory/stock_list.html",
                  {"page": page, "warehouses": Warehouse.objects.all(),
                   "query": query_without_page(request)})


@permission_required("inventory.change_stockitem", raise_exception=True)
def stock_edit(request, pk):
    item = get_object_or_404(StockItem.objects.select_related("product", "warehouse"), pk=pk)
    form = StockForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        log.info("Инвентаризация: %s", item)
        messages.success(request, "Остаток обновлён")
        return redirect("stock_list")
    return render(request, "inventory/stock_form.html", {"form": form, "item": item})


@login_required
def critical(request):
    products = (Product.objects.critical().annotate(order_qty=F("min_stock") * 2 - F("total"))
                .prefetch_related("suppliers").order_by("total"))
    return render(request, "inventory/critical.html", {"products": products})


# ---------- поставщики (CBV) ----------
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    paginate_by = settings.PAGE_SIZE

    def get_queryset(self):
        qs = Supplier.objects.annotate(n_products=Count("products", distinct=True),
                                       n_shipments=Count("shipments", distinct=True))
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(inn__startswith=q) | Q(city__icontains=q))
        return qs.order_by(self.request.GET.get("sort") if self.request.GET.get("sort") in
                           ("name", "-n_products", "city") else "name")


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = self.object.products.with_stock()
        context["shipments"] = self.object.shipments.select_related("product", "warehouse")[:10]
        return context


class SupplierCreateView(PermissionRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    permission_required = "inventory.add_supplier"
    extra_context = {"title": "Новый поставщик"}


class SupplierUpdateView(PermissionRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    permission_required = "inventory.change_supplier"
    extra_context = {"title": "Редактирование поставщика"}


# ---------- поставки (CBV + FBV) ----------
class ShipmentListView(LoginRequiredMixin, ListView):
    model = Shipment
    paginate_by = settings.PAGE_SIZE

    def get_queryset(self):
        qs = Shipment.objects.select_related("product", "supplier", "warehouse")
        status = self.request.GET.get("status")
        return qs.filter(status=status) if status else qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Shipment.Status.choices
        context["query"] = query_without_page(self.request)
        return context


class ShipmentCreateView(PermissionRequiredMixin, CreateView):
    model = Shipment
    form_class = ShipmentForm
    permission_required = "inventory.add_shipment"
    success_url = reverse_lazy("shipment_list")

    def get_initial(self):
        return {"product": self.request.GET.get("product")}

    def form_valid(self, form):
        messages.success(self.request, "Поставка оформлена и ожидает приёмки")
        return super().form_valid(form)


@require_POST
@permission_required("inventory.change_shipment", raise_exception=True)
def shipment_receive(request, pk):
    shipment = get_object_or_404(Shipment.objects.select_related("product", "warehouse"), pk=pk)
    try:
        item = shipment.receive()
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        log.info("Принята поставка №%s, остаток %s", shipment.pk, item.quantity)
        messages.success(request, f"Поставка №{shipment.pk} принята. Остаток «{item.product.name}» "
                                  f"на складе «{item.warehouse.name}»: {item.quantity}")
    return redirect("shipment_list")
