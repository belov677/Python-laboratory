import os


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL",
                             "postgresql+psycopg://lab:lab@localhost:5432/logistics_web")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    PAGE_SIZE = int(os.getenv("PAGE_SIZE", "5"))
    TESTING = False


class TestConfig(Config):
    DATABASE_URL = os.getenv("TEST_DATABASE_URL",
                             "postgresql+psycopg://lab:lab@localhost:5432/logistics_web_test")
    TESTING = True
