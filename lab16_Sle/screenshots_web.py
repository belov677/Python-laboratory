"""Скриншоты интерфейса (Playwright). Сервер: python manage.py runserver 127.0.0.1:5016"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5016"
OUT = Path(__file__).parent / "screenshots"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def shot(page, name):
    page.screenshot(path=str(OUT / f"web_{name}.png"), full_page=True)
    print("saved", name)


def login(page, user, password, save=None):
    page.goto(BASE + "/accounts/login/")
    page.fill("input[name=username]", user)
    page.fill("input[name=password]", password)
    if save:
        shot(page, save)
    page.click("form.form button")


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    anon = browser.new_page(viewport={"width": 1280, "height": 720}, locale="ru-RU")
    anon.goto(BASE + "/"); shot(anon, "index_anon")
    anon.goto(BASE + "/products/"); shot(anon, "login_redirect")
    login(anon, "viewer", "wrong"); shot(anon, "login_error")

    viewer = browser.new_page(viewport={"width": 1280, "height": 720}, locale="ru-RU")
    login(viewer, "viewer", "viewer12345", save="login")
    shot(viewer, "index_viewer")
    viewer.goto(BASE + "/products/"); shot(viewer, "list_viewer")
    r = viewer.goto(BASE + "/products/create/"); print("viewer create:", r.status); shot(viewer, "403")

    m = browser.new_page(viewport={"width": 1280, "height": 720}, locale="ru-RU")
    login(m, "manager", "manager12345")
    m.goto(BASE + "/products/"); shot(m, "list")
    m.goto(BASE + "/products/?page=2"); shot(m, "page2")
    m.goto(BASE + "/products/?q=ноут"); shot(m, "search")
    m.goto(BASE + "/products/?category=building&sort=-price"); shot(m, "filter_sort")
    m.goto(BASE + "/products/?critical=on&sort=total"); shot(m, "filter_critical")
    m.goto(BASE + "/products/1/"); shot(m, "detail")
    m.goto(BASE + "/products/create/")
    m.fill("#id_sku", "bad sku"); m.fill("#id_name", "Товар"); m.fill("#id_price", "-5")
    m.select_option("#id_category", "food"); m.select_option("#id_unit", "м")
    m.click("form.form button"); shot(m, "form_errors")
    m.goto(BASE + "/products/create/")
    m.fill("#id_sku", "OF-5005"); m.fill("#id_name", "Маркер перманентный")
    m.select_option("#id_category", "office"); m.fill("#id_price", "95"); m.fill("#id_min_stock", "50")
    m.check("input[name=suppliers][value='5']"); shot(m, "form")
    m.click("form.form button"); shot(m, "created")
    new_url = m.url
    m.goto(new_url + "edit/"); m.fill("#id_price", "110"); shot(m, "edit")
    m.click("form.form button"); shot(m, "edited")
    m.goto(new_url + "delete/"); shot(m, "delete")
    m.click("button.danger"); shot(m, "deleted")
    m.goto(BASE + "/critical/"); shot(m, "critical")
    m.goto(BASE + "/stock/?warehouse=1&low=1"); shot(m, "stock")
    m.goto(BASE + "/suppliers/"); shot(m, "suppliers")
    m.goto(BASE + "/suppliers/1/"); shot(m, "supplier_detail")
    m.goto(BASE + "/shipments/create/?product=2")
    m.select_option("#id_supplier", "1"); m.select_option("#id_warehouse", "1")
    m.fill("#id_quantity", "10"); m.fill("#id_purchase_price", "16000")
    m.click("form.form button"); shot(m, "shipment_created")
    m.locator("form.inline button.small").first.click(); shot(m, "shipment_received")
    m.goto(BASE + "/statistics/"); shot(m, "statistics")

    a = browser.new_page(viewport={"width": 1500, "height": 760}, locale="ru-RU")
    login(a, "admin", "admin12345")
    a.goto(BASE + "/admin/"); shot(a, "admin_index")
    a.goto(BASE + "/admin/inventory/product/?stock=critical"); shot(a, "admin_products")
    a.goto(BASE + "/admin/inventory/product/1/change/"); shot(a, "admin_product_edit")
    a.goto(BASE + "/admin/inventory/shipment/"); shot(a, "admin_shipments")
    browser.close()
