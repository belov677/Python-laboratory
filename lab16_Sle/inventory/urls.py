from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("statistics/", views.statistics, name="statistics"),
    path("products/", views.product_list, name="product_list"),
    path("products/create/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("stock/", views.stock_list, name="stock_list"),
    path("stock/<int:pk>/edit/", views.stock_edit, name="stock_edit"),
    path("critical/", views.critical, name="critical"),
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/", views.SupplierDetailView.as_view(), name="supplier_detail"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_edit"),
    path("shipments/", views.ShipmentListView.as_view(), name="shipment_list"),
    path("shipments/create/", views.ShipmentCreateView.as_view(), name="shipment_create"),
    path("shipments/<int:pk>/receive/", views.shipment_receive, name="shipment_receive"),
]
