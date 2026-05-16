import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.amazon.in/s?k=badminton+racquet+for+10yr+boy", wait_until="domcontentloaded")
        items = await page.query_selector_all('div[data-component-type="s-search-result"]')
        if items:
            for item in items[:2]:
                title = await item.query_selector('h2')
                print("Title inner_text:", await title.inner_text() if title else "None")
                print("ASIN:", await item.get_attribute('data-asin'))
                print("---")
        else:
            print("No items found")
        await browser.close()
asyncio.run(run())
