import os

import pytest

from core.browser import browser_page, launch_browser
from core.config import Account, Settings, ShopData
from core.reporting import attach_failure, step
from ui.account import Header, RegistrationPage


@pytest.fixture(scope="session")
def settings():
    return Settings.load()


@pytest.fixture(scope="session")
def shop_data():
    return ShopData.load()


@pytest.fixture(scope="session")
def browser(settings):
    with launch_browser(settings) as instance:
        yield instance


@pytest.fixture
def page(browser, settings):
    with browser_page(browser, settings) as instance:
        yield instance


@pytest.fixture(scope="session")
def account(browser, settings, shop_data):
    credentials = Account.create()
    if not os.getenv("SHOP_EMAIL"):
        with browser_page(browser, settings) as registration:
            try:
                with step("Подготовить новую учебную учётную запись через интерфейс"):
                    RegistrationPage(registration).register(credentials, shop_data.customer)
                    Header(registration).logout()
            except Exception:
                attach_failure(registration, "подготовка аккаунта")
                raise
    return credentials


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.failed and report.when in {"setup", "call"}:
        attach_failure(item.funcargs.get("page"), report.when)
