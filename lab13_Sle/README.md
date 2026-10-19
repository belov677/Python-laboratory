# Лабораторная №13 — «Склад — товары» (вариант 17): MongoDB + Redis

```
pip install -r requirements.txt
python app/main.py --reset      # индексы + 24 документа, консольное меню
python explain_demo.py          # индекс до/после (explain)
python stampede_demo.py         # защита от cache stampede
python subscriber.py            # подписчик Pub/Sub
pytest                          # тесты (БД warehouse_test, Redis db 14)
docker compose up               # приложение + MongoDB + Redis в контейнерах
```
