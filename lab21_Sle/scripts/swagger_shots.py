"""Скриншоты Swagger UI (Playwright): python scripts/swagger_shots.py"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "screenshots"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://localhost:8000/swagger")
    page.wait_for_selector(".opblock")
    page.screenshot(path=str(OUT / "swagger.png"), full_page=True)
    block = "#operations-Доставки-create_delivery_deliveries_post"
    page.click(f"{block} .opblock-summary")
    page.wait_for_timeout(500)
    page.locator(block).screenshot(path=str(OUT / "swagger_delivery.png"))
    browser.close()
