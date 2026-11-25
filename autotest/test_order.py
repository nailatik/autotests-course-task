import allure
import pytest

from core.reporting import describe_case, step
from ui.account import LoginPage
from ui.catalog import CartPage, CatalogPage, ProductPage
from ui.checkout import CheckoutPage, OrderPage


@pytest.mark.order
@allure.feature("Оформление заказа")
@allure.title("TC-M-16 · От входа до подтверждённого заказа с оплатой при получении")
@allure.label("case_id", "TC-M-16")
def test_order_cash_on_delivery(page, account, shop_data):
    product = shop_data.product
    describe_case(
        "TC-M-16", "От входа до подтверждённого заказа с оплатой при получении",
        product=product.name, quantity=product.quantity, delivery=shop_data.shipping,
        payment=shop_data.payment,
    )
    login = LoginPage(page)
    with step("Открыть форму входа"):
        login.open_form()
    login.sign_in(account)

    cart = CartPage(page)
    with step("Проверить, что корзина нового прогона пуста"):
        cart.open("/cart")
        cart.require_empty()

    catalog = CatalogPage(page)
    with step("Найти товар по названию и открыть совпавшую карточку"):
        catalog.search(product.query)
        catalog.open_result(product)
    product_page = ProductPage(page)
    with step("Проверить карточку и положить нужное количество в корзину"):
        product_page.verify_product(product)
        product_page.add_to_cart(product)
    with step("Проверить корзину и принять условия продажи"):
        cart.verify_cart(product)
        cart.checkout()

    checkout = CheckoutPage(page)
    checkout.prepare(account, shop_data)
    total = checkout.verify_and_submit(product)

    order = OrderPage(page)
    with step("Проверить подтверждение и номер созданного заказа"):
        number = order.open_created_order()
        allure.attach(number, "Номер демозаказа", allure.attachment_type.TEXT)
    with step("Сверить состав, контакты и итог на странице заказа"):
        order.verify_order(number, total, account, shop_data)
