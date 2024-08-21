import asyncio
from playwright.async_api import async_playwright, BrowserContext, Browser, Locator
from category_identifiers import category_identifiers
from company_model import CompanyModel
import json
from chunk_list import chunk_list
import re
import pandas as pd


class Scraper:
    category_urls = [
        f"https://buildsteel.org/products-and-providers/#fas+steel-supplier-cat:{id}"
        for id in category_identifiers
    ]

    def __init__(self):
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.company_models: list[CompanyModel] = []

    async def start_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            await self.playwright.stop()

    async def scroll_to_bottom(self, page):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    async def start_scrape(self):
        # for url in self.category_urls:
        url = "https://buildsteel.org/products-and-providers/"
        page = await self.context.new_page()
        await page.goto(url)
        # category = re.search(r"/#fas\+steel-supplier-cat:(.*)$", url).group(1)

        # print(f"Scraping category: {category}")

        await self.scroll_to_bottom(page)

        try:
            companies = await page.locator(
                "div[data-grid-id] a:not([style*='display: none'])"
            ).all()

            new_company_models = await asyncio.gather(
                *[
                    self.scrape_company_from_category_page(company_locator)
                    for company_locator in companies
                ]
            )

            filtered_company_models = [
                model for model in new_company_models if model is not None
            ]

            self.company_models.extend(filtered_company_models)
        except Exception as err:
            print(f"error in category: {err}")

        await page.close()

        chunked_companies = chunk_list(self.company_models, 5)

        for chunk in chunked_companies:
            await asyncio.gather(
                *[
                    self.scrape_company(company)
                    for company in chunk
                    if company is not None
                ]
            )

        print(
            json.dumps(
                {"companies": [model.as_dict() for model in self.company_models]},
                indent=4,
            )
        )

        print(f"writing csv for {len(self.company_models)} companies")

        df = pd.DataFrame(self.company_models)
        df.to_csv("data/companies.csv", index=False)

    async def scrape_company_from_category_page(self, company: Locator):
        try:
            class_text = await company.get_attribute("class")
            category = re.search(
                r"-tax-steel-supplier-cat-([\w-]+)", class_text, re.MULTILINE
            ).group(1)

            name = await company.get_attribute("data-order-default")
            url = await company.get_attribute("href")
            address = (
                await company.locator("span")
                .last.locator("p")
                .first.text_content(timeout=60 * 1000)
            )

            return CompanyModel(name, address, category=category, website=url)
        except Exception as err:
            print(f"error scraping company in main page: {err}")
            print("class text:", class_text)
            return None

    async def scrape_company(self, company: CompanyModel):
        print(f"Scraping company: {company.name} - url: {company.website}")
        page = await self.context.new_page()
        await page.goto(company.website)
        page.set_default_timeout(5 * 1000)

        try:
            phone = (
                await page.locator("p", has_text="phone:")
                .first.locator("a")
                .first.get_attribute("href")
            )
            phone = phone.removeprefix("tel:") if phone is not None else None
        except:
            phone = None

        try:
            email = (
                await page.locator("p", has_text="email:")
                .first.locator("a")
                .first.get_attribute("href")
            )
            email = email.removeprefix("mailto:") if email is not None else None
        except:
            email = None

        company.phone = phone
        company.email = email

        await page.close()


async def main():
    scraper = Scraper()
    await scraper.start_browser()
    await scraper.start_scrape()
    await scraper.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
