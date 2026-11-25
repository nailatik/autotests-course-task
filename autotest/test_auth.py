import re
import secrets

import allure
import pytest

from core.reporting import describe_case, step
from ui.account import Header, LoginPage

FIELD_ERRORS = {
    "bad-email": re.compile(r"wrong email|invalid email|valid email", re.I),
}
SERVER_ERRORS = {
    "empty-email": re.compile(r"please enter your email", re.I),
    "empty-password": re.compile(r"credentials provided are incorrect|password.+required|enter your password", re.I),
    "wrong-password": re.compile(r"credentials provided are incorrect|incorrect password", re.I),
    "unknown-account": re.compile(r"no customer account found|credentials provided are incorrect", re.I),
}


@pytest.mark.auth
@allure.feature("Авторизация")
@allure.title("TC-A-02 · Успешный вход ({method})")
@allure.label("case_id", "TC-A-02")
@pytest.mark.parametrize(
    "method",
    [
        pytest.param("click", id="TC-A-02-click"),
        pytest.param("enter", id="TC-A-02-enter"),
    ],
)
def test_email_login(page, account, method):
    title = "Вход кнопкой" if method == "click" else "Вход клавишей Enter"
    describe_case("TC-A-02", title, identifier="email", submit=method)
    login = LoginPage(page)
    with step("Открыть форму входа в гостевой сессии"):
        login.open_form()
        Header(page).require_guest()
    login.sign_in(account, method)


@pytest.mark.auth
@allure.feature("Авторизация")
@allure.title("{case_id} · Отказ во входе ({defect}, {variant})")
@pytest.mark.parametrize(
    "case_id, defect, variant",
    [
        pytest.param("TC-A-03", "empty-email", "empty", id="TC-A-03-empty-email"),
        pytest.param("TC-A-04", "empty-password", "empty", id="TC-A-04-empty-password"),
        pytest.param("TC-A-05", "bad-email", "missing-at", id="TC-A-05-missing-at"),
        pytest.param("TC-A-05", "bad-email", "missing-local-part", id="TC-A-05-missing-local-part"),
        pytest.param("TC-A-05", "bad-email", "missing-domain", id="TC-A-05-missing-domain"),
        pytest.param("TC-A-06", "wrong-password", "different", id="TC-A-06-wrong-password"),
        pytest.param("TC-A-07", "unknown-account", "unregistered", id="TC-A-07-unknown-account"),
    ],
)
def test_email_rejection(page, account, case_id, defect, variant):
    titles = {
        "empty-email": "Пустой email · демонстрация падения",
        "empty-password": "Пустой пароль",
        "bad-email": "Неверный формат email",
        "wrong-password": "Неверный пароль с повторной попыткой",
        "unknown-account": "Неизвестный аккаунт",
    }
    describe_case(case_id, f"{titles[defect]} ({variant})", identifier="email")
    email, password = account.email, account.password
    if defect == "empty-email":
        email = ""
    elif defect == "empty-password":
        password = ""
    elif defect == "bad-email":
        email = {"missing-at": "qa.example.test", "missing-local-part": "@example.test",
                 "missing-domain": "qa@"}[variant]
    elif defect == "unknown-account":
        email = f"absent-{secrets.token_hex(10)}@example.com"
    elif defect == "wrong-password":
        password = f"Wrong!{secrets.token_urlsafe(12)}"

    login = LoginPage(page)
    with step("Открыть форму в гостевой сессии"):
        login.open_form()
        Header(page).require_guest()
    with step("Отправить форму с одним дефектом"):
        login.submit(email, password)
    with step("Проверить ожидаемую ошибку и гостевую сессию"):
        if defect in FIELD_ERRORS:
            login.require_rejection(login.EMAIL_ERROR, FIELD_ERRORS[defect])
        else:
            login.require_rejection(login.SERVER_ERROR, SERVER_ERRORS[defect])
    if defect == "wrong-password":
        login.sign_in(account)
