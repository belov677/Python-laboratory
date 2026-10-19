"""Скриншоты Swagger UI и ReDoc (Playwright + Chromium)."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).parent / "screenshots"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
    page.goto(f"{BASE}/docs")
    page.wait_for_selector(".opblock", timeout=20000)
    page.screenshot(path=OUT / "swagger_overview.png", full_page=True)
    # авторизация через кнопку Authorize (OAuth2 password flow)
    page.click("button.authorize")
    page.fill("#oauth_username", "admin")
    page.fill("#oauth_password", "admin12345")
    page.click(".auth-btn-wrapper button.authorize")
    page.wait_for_selector("button:has-text('Logout')", timeout=10000)
    page.screenshot(path=OUT / "swagger_auth.png")
    page.click("button.btn-done")
    # выполнить GET /items с параметрами
    block = page.locator("#operations-Товары_склада-list_items_items_get")
    block.locator(".opblock-summary").click()
    block.locator("button.try-out__btn").click()
    block.locator("input[placeholder='category']").fill("электроника")
    block.locator("select").nth(0).select_option("price")
    block.locator("select").nth(1).select_option("desc")
    block.locator("button.execute").click()
    block.locator(".responses-wrapper .live-responses-table").wait_for(timeout=10000)
    block.screenshot(path=OUT / "swagger_get_items.png")
    # схема POST /items: request body и модель ответа
    page.reload()
    page.wait_for_selector(".opblock")
    post = page.locator("#operations-Товары_склада-create_item_items_post")
    post.locator(".opblock-summary").click()
    post.locator(".opblock-body").wait_for()
    post.screenshot(path=OUT / "swagger_post_schema.png")
    page.locator("section.models").scroll_into_view_if_needed()
    page.locator("section.models").screenshot(path=OUT / "swagger_schemas.png")
    page.goto(f"{BASE}/redoc")
    page.wait_for_selector("h1", timeout=20000)
    page.wait_for_timeout(1500)
    page.screenshot(path=OUT / "redoc.png")
    browser.close()
print("ok")
