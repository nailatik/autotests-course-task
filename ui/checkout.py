import re
from decimal import Decimal

from playwright.sync_api import expect

from core.reporting import step
from ui.base import BasePage, amount


class CheckoutPage(BasePage):
    def _continue(self, section):
        self.element(f"#opc-{section} .step-title").locator.wait_for(state="visible")
        self.element(f"#opc-{section} .new-address-next-step-button, "
                     f"#opc-{section} .shipping-method-next-step-button, "
                     f"#opc-{section} .payment-method-next-step-button, "
                     f"#opc-{section} .payment-info-next-step-button").click()

    def _billing(self, customer, account):
        prefix = "#BillingNewAddress_"
        for field, value in {
            "FirstName": customer.first_name,
            "LastName": customer.last_name,
            "Email": account.email,
            "City": customer.city,
            "Address1": customer.address,
            "ZipPostalCode": customer.postal_code,
            "PhoneNumber": customer.phone,
        }.items():
            self.element(prefix + field).fill(value)
        self.element(prefix + "CountryId").locator.select_option(label=customer.country)
        self.element(prefix + "StateProvinceId").locator.select_option(label=customer.region)
        self._continue("billing")

    def _choose(self, section, choice):
        radio = self.element(f"#opc-{section} input[type='radio']").locator
        option = self.page.locator(f"#opc-{section} label").filter(
            has_text=re.compile(r"^\s*" + re.escape(choice) + r"(?:\s*\(|\s*$)")
        )
        expect(option).to_have_count(1)
        option_id = option.get_attribute("for")
        if not option_id:
            raise AssertionError("У варианта оформления отсутствует связанное поле")
        selected = radio.and_(self.page.locator(f"[id='{option_id}']"))
        selected.check()
        expect(selected).to_be_checked()
        self._continue(section)

    def prepare(self, account, data):
        with step("Заполнить платёжный адрес и обязательные контакты"):
            expect(self.page).to_have_url(re.compile(r"/onepagecheckout/?$"))
            self._billing(data.customer, account)
        with step("Выбрать доставку на указанный адрес"):
            self._continue("shipping")
            self._choose("shipping_method", data.shipping)
        with step("Выбрать оплату при получении"):
            self._choose("payment_method", data.payment)
            expect(self.element("#checkout-payment-info-load .info").locator).to_be_visible()
            self._continue("payment_info")

    def verify_and_submit(self, product):
        with step("Проверить состав и итог перед отправкой"):
            review = self.element("#checkout-confirm-order-load").locator
            totals = self.element("#checkout-confirm-order-load .cart-total").locator
            expect(totals).to_be_visible()
            verify_summary(review, product)
            total = verify_totals(totals, product)
        with step("Подтвердить демозаказ"):
            self.element("#confirm-order-buttons-container .confirm-order-next-step-button").click()
        return total


def verify_summary(section, product):
    table = section.locator("table.cart, .products table.data-table")
    rows = table.locator("tbody tr")
    expect(rows).to_have_count(1)
    expect(rows.locator(f"a[href='{product.path}']").filter(has_text=product.name)).to_have_count(1)
    headings = [text.strip().casefold() for text in table.locator("thead th").all_inner_texts()]
    cells = rows.locator("td")

    def cell(*labels):
        for label in labels:
            if label in headings:
                return cells.nth(headings.index(label))
        raise AssertionError(f"Не найдена колонка «{labels[0]}» в составе заказа")

    expect(cell("quantity", "qty.")).to_have_text(str(product.quantity), use_inner_text=True)
    assert amount(cell("price").inner_text()) == product.price
    assert amount(cell("total").inner_text()) == product.price * product.quantity


def verify_totals(totals, product):
    def value(label):
        row = totals.locator("tr").filter(has_text=label)
        return amount(row.locator("td").last.inner_text())

    subtotal = value(re.compile(r"Sub-Total\s*:"))
    shipping = value(re.compile(r"Shipping\s*:"))
    tax = value(re.compile(r"Tax\s*:"))
    total = value(re.compile(r"^\s*(?:Order )?Total\s*:"))
    assert subtotal == product.price * product.quantity
    # Cash on Delivery может добавить отдельную плату за выбранный способ оплаты.
    fee = Decimal("0")
    fee_row = totals.locator("tr").filter(has_text=re.compile(r"Payment method additional fee", re.I))
    if fee_row.count():
        fee = amount(fee_row.locator("td").last.inner_text())
    assert total == subtotal + shipping + tax + fee
    return total


class OrderPage(BasePage):
    def open_created_order(self):
        expect(self.page).to_have_url(re.compile(r"/checkout/completed(?:/\d+)?/?$"))
        expect(self.element(".order-completed .title").locator).to_contain_text(
            "Your order has been successfully processed"
        )
        details = self.element(".order-completed .details")
        text = details.text()
        match = re.search(r"Order number:\s*(\d+)", text, re.I)
        if not match or int(match.group(1)) < 1:
            raise AssertionError("На странице подтверждения отсутствует номер заказа")
        details.locator.locator("a[href^='/orderdetails/']").click(no_wait_after=True)
        return match.group(1)

    def verify_order(self, order_number, total, account, data):
        expect(self.page).to_have_url(re.compile(r"/orderdetails/" + order_number + r"/?$"))
        details = self.element(".order-details-page").locator
        expect(details.locator(".order-number")).to_contain_text(order_number)
        verify_summary(details, data.product)
        displayed_total = details.locator(".order-overview .order-total").inner_text()
        assert amount(displayed_total.rpartition(":")[2]) == total

        address_columns = details.locator(".order-details-area > table > tbody > tr > td")
        expect(address_columns).to_have_count(2)
        billing = address_columns.nth(0).inner_text()
        shipping = address_columns.nth(1).inner_text()
        customer = data.customer
        contact_fields = (customer.first_name, customer.last_name, customer.address, customer.phone)
        if not all(value in billing and value in shipping for value in contact_fields):
            raise AssertionError("Адрес или контакты заказа отличаются от введённых")
        if account.email not in billing or account.email not in shipping:
            raise AssertionError("Email в заказе отличается от email пользователя")
        if data.shipping not in shipping or data.payment not in billing:
            raise AssertionError("Способ доставки или оплаты отличается от выбранного")
