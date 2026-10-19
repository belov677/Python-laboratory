"""Автоматические тесты (python manage.py test)."""
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import ProductForm
from .models import Product, Shipment, StockItem, Supplier, Warehouse


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w1 = Warehouse.objects.create(name="Центральный", city="Москва", address="ул. 1")
        cls.w2 = Warehouse.objects.create(name="Северный", city="СПб", address="ул. 2")
        cls.sup = Supplier.objects.create(name="ТехноПоставка", inn="7701234567",
                                          email="a@b.ru", city="Москва")
        cls.sup2 = Supplier.objects.create(name="Офис-Плюс", inn="7704567890",
                                           email="c@d.ru", city="Тула")
        cls.products = []
        for i in range(12):
            p = Product.objects.create(sku=f"EL-{100 + i}", name=f"Товар электроника {i:02d}",
                                       category="electronics", price=Decimal(100 + i * 10),
                                       min_stock=10)
            p.suppliers.add(cls.sup)
            StockItem.objects.create(product=p, warehouse=cls.w1, quantity=i * 2)
            cls.products.append(p)
        cls.paper = Product.objects.create(sku="OF-500", name="Бумага A4", category="office",
                                           price=Decimal("420.00"), min_stock=5)
        cls.paper.suppliers.add(cls.sup2)
        StockItem.objects.create(product=cls.paper, warehouse=cls.w2, quantity=50)
        cls.viewer = User.objects.create_user("viewer", password="viewer12345")
        managers = Group.objects.create(name="Менеджеры")
        managers.permissions.set(Permission.objects.filter(content_type__app_label="inventory"))
        cls.manager = User.objects.create_user("manager", password="manager12345")
        cls.manager.groups.add(managers)
        cls.admin = User.objects.create_superuser("admin", "admin@x.ru", "admin12345")

    def login(self, user):
        self.client.force_login(user)


class PageTests(BaseTest):
    def test_index_page(self):
        r = self.client.get(reverse("index"))
        self.assertContains(r, "СкладУчёт")
        self.assertEqual(r.context["products"], 13)
        self.assertEqual(r.context["critical"], 5)  # остатки 0, 2, 4, 6, 8 < 10

    def test_list_requires_login(self):
        r = self.client.get(reverse("product_list"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('product_list')}")

    def test_list_and_pagination(self):
        self.login(self.viewer)
        r = self.client.get(reverse("product_list"))
        self.assertEqual(len(r.context["page"]), 10)
        self.assertEqual(r.context["page"].paginator.num_pages, 2)
        r = self.client.get(reverse("product_list") + "?page=2")
        self.assertEqual(len(r.context["page"]), 3)

    def test_detail_page_with_relations(self):
        self.login(self.viewer)
        r = self.client.get(reverse("product_detail", args=[self.paper.pk]))
        self.assertContains(r, "Бумага A4")
        self.assertContains(r, "Офис-Плюс")      # M2M поставщики
        self.assertContains(r, "Северный")       # остаток на складе

    def test_detail_404(self):
        self.login(self.viewer)
        self.assertEqual(self.client.get(reverse("product_detail", args=[99999])).status_code, 404)

    def test_search(self):
        self.login(self.viewer)
        r = self.client.get(reverse("product_list"), {"q": "бумага"})
        self.assertEqual([p.sku for p in r.context["page"]], ["OF-500"])
        r = self.client.get(reverse("product_list"), {"q": "EL-10"})
        self.assertEqual(r.context["total"], 10)

    def test_filters(self):
        self.login(self.viewer)
        r = self.client.get(reverse("product_list"), {"category": "office"})
        self.assertEqual(r.context["total"], 1)
        r = self.client.get(reverse("product_list"), {"supplier": self.sup.pk, "critical": "on"})
        self.assertEqual(r.context["total"], 5)

    def test_sorting(self):
        self.login(self.viewer)
        r = self.client.get(reverse("product_list"), {"sort": "-price"})
        prices = [p.price for p in r.context["page"]]
        self.assertEqual(prices, sorted(prices, reverse=True))
        r = self.client.get(reverse("product_list"), {"sort": "total"})
        self.assertEqual(r.context["page"][0].total, 0)

    def test_statistics(self):
        self.login(self.viewer)
        r = self.client.get(reverse("statistics"))
        self.assertEqual(r.context["count"], 13)
        self.assertEqual(r.context["units"], sum(i * 2 for i in range(12)) + 50)
        self.assertEqual(r.context["critical"], 5)


class CrudTests(BaseTest):
    data = {"sku": "of-777", "name": "Степлер", "category": "office", "unit": "шт",
            "price": "340", "min_stock": "20", "description": ""}

    def test_create(self):
        self.login(self.manager)
        r = self.client.post(reverse("product_create"), {**self.data, "suppliers": [self.sup2.pk]})
        product = Product.objects.get(sku="OF-777")       # артикул приведён к верхнему регистру
        self.assertRedirects(r, product.get_absolute_url())
        self.assertEqual(list(product.suppliers.all()), [self.sup2])

    def test_update(self):
        self.login(self.manager)
        r = self.client.get(reverse("product_edit", args=[self.paper.pk]))
        self.assertContains(r, 'value="Бумага A4"')        # форма с текущими значениями
        self.client.post(reverse("product_edit", args=[self.paper.pk]),
                         {**self.data, "sku": "OF-500", "name": "Бумага A4 Premium", "price": "500"})
        self.paper.refresh_from_db()
        self.assertEqual((self.paper.name, self.paper.price), ("Бумага A4 Premium", Decimal("500")))

    def test_delete_with_confirmation(self):
        self.login(self.manager)
        r = self.client.get(reverse("product_delete", args=[self.paper.pk]))
        self.assertContains(r, "Вы действительно хотите удалить")
        self.client.post(reverse("product_delete", args=[self.paper.pk]))
        self.assertFalse(Product.objects.filter(pk=self.paper.pk).exists())
        self.assertFalse(StockItem.objects.filter(product_id=self.paper.pk).exists())  # CASCADE

    def test_validation(self):
        form = ProductForm({**self.data, "sku": "bad sku", "price": "-1", "unit": "м",
                            "category": "food"})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors), {"sku", "price", "unit"})
        self.login(self.manager)
        r = self.client.post(reverse("product_create"), {**self.data, "sku": "EL-100"})
        self.assertContains(r, "уже существует")


class AuthTests(BaseTest):
    def test_login_and_logout(self):
        r = self.client.post(reverse("login"), {"username": "viewer", "password": "viewer12345"})
        self.assertRedirects(r, reverse("index"))
        self.assertContains(self.client.get(reverse("index")), "Вы вошли как <b>viewer</b>")
        r = self.client.post(reverse("login"), {"username": "viewer", "password": "wrong"})
        self.assertContains(r, "Неверное имя пользователя или пароль")

    def test_viewer_cannot_modify(self):
        self.login(self.viewer)
        self.assertEqual(self.client.get(reverse("product_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("product_delete", args=[self.paper.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("supplier_create")).status_code, 403)
        self.assertNotContains(self.client.get(reverse("product_list")), "+ Добавить товар")
        self.assertTrue(Product.objects.filter(pk=self.paper.pk).exists())

    def test_admin_and_manager_permissions(self):
        self.login(self.manager)
        self.assertEqual(self.client.get(reverse("product_create")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)  # не staff
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:inventory_product_changelist")).status_code, 200)
        r = self.client.get(reverse("admin:inventory_product_changelist"), {"stock": "critical"})
        self.assertEqual(r.context["cl"].result_count, 5)

    def test_passwords_are_hashed(self):
        self.assertTrue(self.viewer.password.startswith("pbkdf2_sha256$"))
        self.assertNotIn("viewer12345", self.viewer.password)


class RelationTests(BaseTest):
    def test_relations(self):
        self.assertEqual(self.sup.products.count(), 12)                       # M2M обратная
        self.assertEqual(list(self.paper.warehouses.all()), [self.w2])       # M2M through
        self.assertEqual(self.w1.stock_items.count(), 12)                    # FK обратная

    def test_receive_shipment_increases_stock(self):
        p = self.products[0]
        sh = Shipment.objects.create(product=p, supplier=self.sup, warehouse=self.w2,
                                     quantity=30, purchase_price=Decimal("70"))
        item = sh.receive()
        self.assertEqual((item.warehouse, item.quantity), (self.w2, 30))
        self.assertEqual(Product.objects.with_stock().get(pk=p.pk).total, 30)
        with self.assertRaises(ValidationError):
            sh.receive()                                                    # повторно нельзя

    def test_shipment_supplier_must_supply_product(self):
        sh = Shipment(product=self.paper, supplier=self.sup, warehouse=self.w1, quantity=1,
                      purchase_price=Decimal("1"))
        with self.assertRaises(ValidationError):
            sh.full_clean()

    def test_receive_via_web(self):
        sh = Shipment.objects.create(product=self.paper, supplier=self.sup2, warehouse=self.w2,
                                     quantity=10, purchase_price=Decimal("300"))
        self.login(self.manager)
        r = self.client.post(reverse("shipment_receive", args=[sh.pk]), follow=True)
        self.assertContains(r, "принята")
        self.assertEqual(StockItem.objects.get(product=self.paper, warehouse=self.w2).quantity, 60)

    def test_n_plus_one_fixed(self):
        with self.assertNumQueries(1):
            names = [(i.product.name, i.warehouse.name)
                     for i in StockItem.objects.select_related("product", "warehouse")]
        self.assertEqual(len(names), 13)
        with self.assertNumQueries(2):
            [list(p.suppliers.all()) for p in Product.objects.prefetch_related("suppliers")]
