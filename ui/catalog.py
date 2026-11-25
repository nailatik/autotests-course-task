import re

from playwright.sync_api import expect

from ui.base import BasePage, amount


class CatalogPage(BasePage):
    def search(self, query):
        self.element("#small-searchterms").fill(query)
        self.element("form[action='/search'] .search-box-button").click(navigates=True)
        expect(self.element(".search-results").locator).to_be_visible()

    def open_result(self, product):
        cards = self.element(".search-results .product-item").locator
        expect(cards.first).to_be_visible()
        names = cards.locator(".product-title a").all_inner_texts()
        assert all(product.query.casefold() in name.casefold() for name in names)
        link = self.element(f".search-results .product-title a[href='{product.path}']")
        expect(link.locator).to_have_text(product.name)
        matched_card = cards.filter(has=self.page.locator(f"a[href='{product.path}']"))
        assert amount(matched_card.locator(".actual-price").inner_text()) == product.price
        link.click(navigates=True)


class ProductPage(BasePage):
    def verify_product(self, product):
        expect(self.page).to_have_url(re.compile(re.escape(product.path) + "$"))
        expect(self.element(".product-name h1").locator).to_have_text(product.name)
        expect(self.element(".stock .value").locator).to_have_text(product.availability)
        assert amount(self.element(".product-price [itemprop='price']").text()) == product.price
        expect(self.element(".add-to-cart-button").locator).to_be_enabled()

    def add_to_cart(self, product):
        self.element(".add-to-cart .qty-input").fill(str(product.quantity))
        self.element(".add-to-cart-button").click()
        message = self.element("#bar-notification.success")
        expect(message.locator).to_contain_text("The product has been added")
        message.locator.locator("a[href='/cart']").click(no_wait_after=True)
        expect(self.element(".order-summary-content .cart").locator).to_be_visible()


class CartPage(BasePage):
    def require_empty(self):
        expect(self.element(".order-summary-content").locator).to_contain_text(
            "Your Shopping Cart is empty!"
        )

    def verify_cart(self, product):
        rows = self.element(".cart tbody tr").locator
        expect(rows).to_have_count(1)
        expect(rows.locator(f"a.product-name[href='{product.path}']")).to_have_text(product.name)
        expect(rows.locator("input.qty-input")).to_have_value(str(product.quantity))
        assert amount(rows.locator(".product-unit-price").inner_text()) == product.price
        assert amount(rows.locator(".product-subtotal").inner_text()) == product.price * product.quantity
        subtotal = self.element(".cart-total .cart-total-left").locator.filter(has_text="Sub-Total")
        subtotal_value = subtotal.locator("xpath=following-sibling::td").inner_text()
        assert amount(subtotal_value) == product.price * product.quantity

    def checkout(self):
        self.element("#termsofservice").locator.check()
        expect(self.element("#termsofservice").locator).to_be_checked()
        self.element("#checkout").click(navigates=True)
