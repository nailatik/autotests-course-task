import re

from playwright.sync_api import expect

from core.reporting import step
from ui.base import BasePage


class Header(BasePage):
    def require_guest(self):
        expect(self.element(".header-links .ico-login").locator).to_be_visible()
        expect(self.element(".header-links .ico-logout").locator).to_have_count(0)
        expect(self.element(".header-links .account").locator).to_have_count(0)

    def require_account(self, email):
        expect(self.element(".header-links .ico-logout").locator).to_be_visible()
        if self.element(".header-links .account").text().casefold() != email.casefold():
            raise AssertionError("В шапке отображается другая учётная запись")

    def logout(self):
        self.element(".header-links .ico-logout").click(navigates=True)
        self.require_guest()


class LoginPage(BasePage):
    EMAIL_ERROR = "span[data-valmsg-for='Email']"
    SERVER_ERROR = ".returning-wrapper .validation-summary-errors"

    def open_form(self):
        self.open("/login")
        self.page.wait_for_load_state("domcontentloaded")
        expect(self.element(".returning-wrapper .login-button").locator).to_be_visible()

    def submit(self, email, password, method="click"):
        self.element("#Email").fill(email)
        field = self.element("#Password")
        expect(field.locator).to_have_attribute("type", "password")
        field.fill(password)
        if method == "enter":
            field.locator.press("Enter", no_wait_after=True)
        else:
            self.element(".returning-wrapper .login-button").click(navigates=True)

    def sign_in(self, account, method="click"):
        with step("Отправить форму входа по email"):
            self.submit(account.email, account.password, method)
        with step("Проверить переход на главную и личность пользователя"):
            expect(self.page).to_have_url(re.compile(r"^https?://[^/]+/$"))
            Header(self.page).require_account(account.email)

    def require_rejection(self, error_selector, expected):
        message = self.element(error_selector).locator
        expect(message).to_be_visible()
        if not expected.search(message.inner_text()):
            raise AssertionError("Форма показала сообщение другого класса")
        Header(self.page).require_guest()
        expect(self.page).to_have_url(re.compile(r"/login(?:\?.*)?$"))


class RegistrationPage(BasePage):
    def register(self, account, customer):
        self.open("/register")
        for selector, value in {
            "#FirstName": customer.first_name,
            "#LastName": customer.last_name,
            "#Email": account.email,
            "#Password": account.password,
            "#ConfirmPassword": account.password,
        }.items():
            self.element(selector).fill(value)
        self.element("#register-button").click(navigates=True)
        expect(self.element(".registration-result-page .result").locator).to_contain_text(
            "Your registration completed"
        )
        Header(self.page).require_account(account.email)
