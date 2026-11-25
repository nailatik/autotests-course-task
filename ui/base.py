from decimal import Decimal

from playwright.sync_api import Locator, Page, expect

from core.reporting import logger


class BaseElement:
    def __init__(self, parent: Page | Locator, selector: str):
        self.locator = parent.locator(selector)
        self.selector = selector

    def click(self, *, navigates=False):
        logger.debug("Нажатие %s", self.selector)
        self.locator.click(no_wait_after=navigates)

    def fill(self, value: str):
        logger.debug("Заполнение %s", self.selector)
        self.locator.fill(value)

    def text(self) -> str:
        return self.locator.inner_text().strip()


def amount(text: str) -> Decimal:
    cleaned = text.strip().removeprefix("$").replace(",", "")
    try:
        return Decimal(cleaned)
    except ArithmeticError:
        raise AssertionError("Цена отображается в неожиданном формате") from None


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def element(self, selector):
        return BaseElement(self.page, selector)

    def open(self, path):
        response = self.page.goto(path, wait_until="commit")
        if response and not response.ok:
            raise AssertionError(f"Стенд вернул HTTP {response.status}")
        captcha = self.page.locator(
            "script[src*='recaptcha'], iframe[src*='recaptcha'], "
            "[name='g-recaptcha-response'], .g-recaptcha, "
            "iframe[src*='challenges.cloudflare.com']"
        )
        self.page.locator("body").wait_for(state="attached")
        expect(captcha, "На стенде включена CAPTCHA").to_have_count(0, timeout=1000)
