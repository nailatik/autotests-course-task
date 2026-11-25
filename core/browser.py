import os

from contextlib import contextmanager

from playwright.sync_api import expect, sync_playwright

from core.reporting import logger, step


@contextmanager
def launch_browser(settings):
    with step("Запустить браузер"):
        driver = sync_playwright().start()
        try:
            engine = getattr(driver, settings.browser)
            args = []
            if (
                settings.headed and settings.browser == "chromium"
                and os.getenv("WAYLAND_DISPLAY") and not os.getenv("DISPLAY")
            ):
                args.append("--ozone-platform=wayland")
            browser = engine.launch(
                headless=not settings.headed, executable_path=settings.executable,
                slow_mo=settings.slow_mo, args=args,
            )
        except BaseException:
            driver.stop()
            raise
        expect.set_options(timeout=settings.timeout)
    try:
        yield browser
    finally:
        browser.close()
        driver.stop()


@contextmanager
def browser_page(browser, settings):
    with step("Открыть чистый браузерный контекст"):
        context = browser.new_context(base_url=settings.base_url, locale="en-US")
        context.set_default_timeout(settings.timeout)
        context.set_default_navigation_timeout(settings.navigation_timeout)
        page = context.new_page()
        logger.debug("Новый контекст, тайм-аут действия %d мс", settings.timeout)
    try:
        yield page
    finally:
        context.close()
