import logging
import re
from contextlib import contextmanager

import allure
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout

logger = logging.getLogger("shop")


@contextmanager
def step(title):
    with allure.step(title):
        logger.info("%s", title)
        try:
            yield
        except PlaywrightError as error:
            code = re.search(r"\bnet::ERR_[A-Z_]+\b", str(error))
            if code:
                reason = f"Ошибка навигации {code.group()}"
            elif isinstance(error, PlaywrightTimeout):
                reason = "Превышен тайм-аут ожидания Playwright"
            else:
                reason = "Ошибка взаимодействия Playwright"
            logger.error("%s | %s", title, reason)
            raise RuntimeError(f"{title} — {reason}") from None
        except AssertionError:
            logger.error("Проверка не выполнена | %s", title)
            raise


def attach_failure(page, phase):
    if not page or page.is_closed():
        allure.attach(
            f"Фаза {phase}. Страница браузера недоступна.",
            "Причина отсутствия скриншота",
            allure.attachment_type.TEXT,
        )
        return

    # Закрываем зоны, в которых сайт может показывать контакты или значения полей.
    private = page.locator(
        "input, textarea, select, iframe, .header-links, .billing-info, "
        ".shipping-info, .order-review-data, .order-details-area, .address-list, .address-item, .edit-address, "
        ".select-billing-address, .select-shipping-address, .validation-summary-errors"
    )
    try:
        picture = page.screenshot(
            mask=[private], mask_color="#242424", animations="disabled", timeout=4000,
        )
    except PlaywrightError:
        allure.attach(
            f"Фаза {phase}. Playwright не смог сделать снимок страницы.",
            "Причина отсутствия скриншота",
            allure.attachment_type.TEXT,
        )
    else:
        allure.attach(picture, f"Состояние страницы · {phase}", allure.attachment_type.PNG)


def describe_case(case_id, title, **parameters):
    allure.dynamic.title(f"{case_id} · {title}")
    allure.dynamic.label("case_id", case_id)
    for name, value in parameters.items():
        allure.dynamic.parameter(name, value)
