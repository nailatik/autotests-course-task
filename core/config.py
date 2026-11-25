import os
import re
import secrets
import tomllib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEMO_URL = "https://demowebshop.tricentis.com"


@dataclass(frozen=True)
class Settings:
    base_url: str = field(repr=False)
    browser: str
    headed: bool
    timeout: int
    navigation_timeout: int
    slow_mo: int
    executable: str | None = field(repr=False)

    @classmethod
    def load(cls):
        base_url = os.getenv("SHOP_BASE_URL", DEMO_URL).rstrip("/")
        url = urlparse(base_url)
        if url.scheme not in {"http", "https"} or not url.hostname or (
            url.username or url.password or url.path or url.query or url.fragment
        ):
            raise ValueError("SHOP_BASE_URL должен содержать только схему и адрес стенда")
        browser = os.getenv("SHOP_BROWSER", "chromium")
        if browser not in {"chromium", "firefox", "webkit"}:
            raise ValueError("SHOP_BROWSER: chromium, firefox или webkit")
        timeout = int(os.getenv("SHOP_TIMEOUT_MS", "30000"))
        navigation_timeout = int(os.getenv("SHOP_NAVIGATION_TIMEOUT_MS", "35000"))
        if min(timeout, navigation_timeout) <= 0:
            raise ValueError("Тайм-ауты должны быть положительными")
        slow_mo = int(os.getenv("SHOP_SLOW_MO_MS", "0"))
        if slow_mo < 0:
            raise ValueError("SHOP_SLOW_MO_MS должен быть неотрицательным")
        return cls(
            base_url, browser, os.getenv("SHOP_HEADED") == "1", timeout,
            navigation_timeout, slow_mo, os.getenv("SHOP_BROWSER_EXECUTABLE"),
        )


@dataclass(frozen=True)
class Product:
    path: str
    query: str
    name: str
    availability: str
    price: Decimal
    quantity: int


@dataclass(frozen=True, repr=False)
class Customer:
    first_name: str
    last_name: str
    country: str
    region: str
    city: str
    address: str
    postal_code: str
    phone: str


@dataclass(frozen=True)
class ShopData:
    product: Product
    customer: Customer = field(repr=False)
    shipping: str
    payment: str

    @classmethod
    def load(cls):
        source = Path(os.getenv("SHOP_DATA", ROOT / "data/demo.toml"))
        with source.open("rb") as file:
            data = tomllib.load(file)
        product = dict(data["product"])
        product["price"] = Decimal(product["price"])
        if not re.fullmatch(r"/[a-z0-9-]+", product["path"]):
            raise ValueError("product.path должен быть относительным URL карточки")
        if product["quantity"] < 1 or product["price"] <= 0:
            raise ValueError("Цена и количество товара должны быть положительными")
        return cls(Product(**product), Customer(**data["customer"]), **data["order"])


@dataclass(frozen=True, repr=False)
class Account:
    email: str
    password: str

    @classmethod
    def create(cls):
        email = os.getenv("SHOP_EMAIL")
        password = os.getenv("SHOP_PASSWORD")
        if bool(email) != bool(password):
            raise ValueError("Задайте SHOP_EMAIL и SHOP_PASSWORD вместе")
        return cls(
            email or f"qa-{secrets.token_hex(10)}@example.com",
            password or f"Qa!{secrets.token_urlsafe(18)}",
        )
