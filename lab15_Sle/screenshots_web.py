"""Скриншоты страниц приложения (Playwright, Chromium)."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5015"
OUT = Path(__file__).parent / "screenshots"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def shot(page, name, full=True):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("saved", name)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    page = browser.new_page(viewport={"width": 1280, "height": 760})
    page.goto(BASE + "/"); shot(page, "web_index")
    page.goto(BASE + "/shipments"); shot(page, "web_list")
    page.goto(BASE + "/shipments?q=Казань&sort=cost&order=asc"); shot(page, "web_search")
    page.goto(BASE + "/shipments?status=IN_TRANSIT&client_id=3"); shot(page, "web_filter")
    page.goto(BASE + "/shipments?page=2"); shot(page, "web_page2")
    # создание с ошибками валидации
    page.goto(BASE + "/shipments/new")
    page.fill("input[name=origin]", "М")
    page.fill("input[name=distance_km]", "-10")
    page.click("form.form button"); shot(page, "web_create_errors")
    # успешное создание
    page.goto(BASE + "/shipments/new")
    page.select_option("select[name=client_id]", "2")
    page.fill("input[name=origin]", "Казань"); page.fill("input[name=destination]", "Уфа")
    page.fill("input[name=distance_km]", "520")
    page.locator("input[name=cargo_description]").nth(0).fill("Мебель офисная")
    page.locator("input[name=cargo_weight]").nth(0).fill("200")
    page.locator("input[name=cargo_description]").nth(1).fill("Зеркала")
    page.locator("input[name=cargo_weight]").nth(1).fill("35")
    page.locator("select[name=cargo_type]").nth(1).select_option("хрупкий")
    shot(page, "web_create_form")
    page.click("form.form button"); shot(page, "web_created")
    # смена статуса нового отправления
    page.fill("input[name=location]", "Набережные Челны")
    page.click("form.inline button"); shot(page, "web_status")
    # редактирование
    page.goto(BASE + "/shipments/4/edit")
    page.fill("input[name=distance_km]", "800"); shot(page, "web_edit")
    page.click("form.form button"); shot(page, "web_edited")
    # удаление
    page.goto(BASE + "/shipments/5/delete"); shot(page, "web_delete")
    page.click("button.danger"); shot(page, "web_deleted")
    page.goto(BASE + "/clients/1"); shot(page, "web_client")
    page.goto(BASE + "/track?number=LG-00002"); shot(page, "web_track")
    page.goto(BASE + "/no-such-page"); shot(page, "web_404")
    page.goto(BASE + "/api/shipments/2"); shot(page, "web_api_json")
    browser.close()
