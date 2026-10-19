"""Тесты HTML-страниц."""


def test_index_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Создание и отслеживание отправлений" in r.get_data(as_text=True)


def test_list_search_filter_sort(client):
    html = client.get("/shipments?q=Казань").get_data(as_text=True)
    assert "LG-00005" in html and "LG-00002" not in html
    html = client.get("/shipments?status=IN_TRANSIT").get_data(as_text=True)
    assert "LG-00002" in html and "LG-00005" not in html
    html = client.get("/shipments?client_id=2&sort=cost&order=asc").get_data(as_text=True)
    assert html.index("LG-00005") < html.index("LG-00006")


def test_pagination(client):
    html = client.get("/shipments?page=2").get_data(as_text=True)
    assert 'class="current"' in html and "найдено: 7" in html


def test_detail_shows_tracking_history(client):
    html = client.get("/shipments/1").get_data(as_text=True)
    assert "Тверь" in html and "доставлено" in html


def test_create_via_form(client):
    r = client.post("/shipments/new", data={
        "client_id": "2", "origin": "Казань", "destination": "Уфа", "distance_km": "520",
        "cargo_description": ["Мебель", ""], "cargo_weight": ["200", ""],
        "cargo_type": ["обычный", "обычный"]}, follow_redirects=True)
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "LG-00008 создано" in html


def test_create_form_validation(client):
    r = client.post("/shipments/new", data={"client_id": "", "origin": "М", "destination": "",
                                            "distance_km": "-1"})
    html = r.get_data(as_text=True)
    assert r.status_code == 400
    assert "Выберите существующего клиента" in html and "Добавьте хотя бы один груз" in html


def test_edit_and_status_and_delete(client):
    r = client.post("/shipments/4/edit", data={
        "client_id": "1", "origin": "Москва", "destination": "Казань", "distance_km": "800",
        "cargo_description": ["Кресла"], "cargo_weight": ["60"], "cargo_type": ["обычный"]},
        follow_redirects=True)
    assert "Изменения сохранены" in r.get_data(as_text=True)
    r = client.post("/shipments/4/status", data={"status": "IN_TRANSIT", "location": "Владимир"},
                    follow_redirects=True)
    assert "Статус изменён: в пути" in r.get_data(as_text=True)
    r = client.post("/shipments/5/delete", follow_redirects=True)
    assert "LG-00005 удалено" in r.get_data(as_text=True)
    assert client.get("/shipments/5").status_code == 404


def test_404_and_500_pages(client):
    assert "Страница не найдена" in client.get("/unknown").get_data(as_text=True)
    r = client.get("/boom")
    assert r.status_code == 500 and "Внутренняя ошибка" in r.get_data(as_text=True)


def test_csrf_required(app):
    app.config["WTF_CSRF_DISABLED"] = False
    r = app.test_client().post("/shipments/1/delete")
    assert r.status_code == 400 and "CSRF" in r.get_data(as_text=True)


def test_track_redirect(client):
    r = client.get("/track?number=lg-00002")
    assert r.status_code == 302 and r.headers["Location"].endswith("/shipments/2")
