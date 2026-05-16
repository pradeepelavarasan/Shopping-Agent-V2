import asyncio
import re
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from schemas import Product

async def handle_amazon_interstitials(page):
    """Detects and clicks 'Continue shopping' or similar bot-check buttons."""
    try:
        # 2-4 second delay to mimic human reaction/rendering
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        # Check for the common 'Continue shopping' button text
        continue_btn = await page.query_selector('text="Continue shopping"')
        if not continue_btn:
             continue_btn = await page.query_selector('a:has-text("Continue shopping")')
        
        if continue_btn:
            print("Detected 'Continue shopping' interstitial. Clicking to proceed...")
            await continue_btn.click()
            await page.wait_for_load_state("networkidle", timeout=5000)
    except:
        pass

async def scrape_amazon_top_3(query: str) -> list[Product]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto(f"https://www.amazon.in/s?k={query.replace(' ', '+')}", wait_until="domcontentloaded")
        await handle_amazon_interstitials(page)
        
        # Extra 2-4s delay after search results appear
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        # Wait for product items
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        
        # Wait for product items
        try:
            await page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=15000)
        except Exception:
            title = await page.title()
            print(f"Timeout waiting for search results. Page title: {title}")
            if "Sorry" in title or "Robot" in title:
                await browser.close()
                raise Exception("Amazon bot detection triggered. Could not scrape products.")
            await page.screenshot(path="amazon_error.png")
            await browser.close()
            return []
            
        items = await page.query_selector_all('div[data-component-type="s-search-result"]')
        # 1. Relevancy Constraint: Only look at the top 20 results.
        # This accounts for initial sponsored items while avoiding irrelevant "drift" at the bottom.
        items = items[:20]
        print(f"Analyzing top {len(items)} results for relevancy...")
        
        organic_products = []
        filtered_products = []
        
        for item in items:
            # 1. Advanced Product Filtering: Identify and skip sponsored products
            is_sponsored = False
            reason = ""
            try:
                # Amazon uses various markers for sponsored items
                sponsored_marker = await item.query_selector('.s-sponsored-label-info-icon, .s-label-popover-default, .puis-sponsored-label-text')
                
                # Check for "Sponsored" only in specific label containers, not the whole text content
                # to avoid false positives with "Deal of the day" or "Limited time deal" tags.
                sponsored_label = await item.query_selector('span:text-is("Sponsored"), span:text-is("AD")')
                
                if sponsored_marker or sponsored_label:
                    is_sponsored = True
                    reason = "Sponsored/AD"
            except:
                pass

            asin = await item.get_attribute('data-asin')
            if not asin:
                continue
                
            # Extract title
            title_el = await item.query_selector('h2')
            title = await title_el.inner_text() if title_el else ""
            
            # Extract url
            link_el = await item.query_selector('h2 a')
            if not link_el:
                link_el = await item.query_selector('a.a-link-normal')
            url = await link_el.get_attribute('href') if link_el else ""
            if url and not url.startswith('http'):
                url = f"https://www.amazon.in{url}"
                
            # Extract price (try multiple common Amazon price selectors)
            price_el = await item.query_selector('.a-price .a-offscreen')
            if not price_el:
                price_el = await item.query_selector('.a-color-price')
            if not price_el:
                price_el = await item.query_selector('.apexPriceToPay .a-offscreen')
            
            price = ""
            if price_el:
                price = await price_el.inner_text()
            else:
                # Fallback: check if it's a "Buying Options" link which often contains price
                buying_options = await item.query_selector('a[href*="buyingOptions"]')
                if buying_options:
                    price = "See Buying Options"
            
            # Clean up price string (remove any non-numeric noise if needed, but keeping currency)
            price = price.strip() if price else "N/A"
            
            # Extract reviews count
            reviews_el = await item.query_selector('span.s-underline-text, span[aria-label*="ratings"]')
            
            reviews_count = 0
            if reviews_el:
                aria_label = await reviews_el.get_attribute('aria-label')
                text = await reviews_el.inner_text()
                raw_val = (aria_label or text or "").lower()
                
                # Handle cases like "1.2k", "1,200", "50"
                match = re.search(r'([\d,\.]+)\s*([km]?)', raw_val)
                if match:
                    val_str = match.group(1).replace(',', '')
                    suffix = match.group(2)
                    try:
                        reviews_count = float(val_str)
                        if suffix == 'k':
                            reviews_count *= 1000
                        elif suffix == 'm':
                            reviews_count *= 1000000
                        reviews_count = int(reviews_count)
                    except:
                        reviews_count = 0

            # Extract rating
            rating_el = await item.query_selector('span.a-icon-alt')
            if not rating_el:
                rating_el = await item.query_selector('i[class*="a-icon-star"] span')
            
            rating = ""
            if rating_el:
                val = await rating_el.inner_text() or ""
                match = re.search(r'(\d+\.?\d*)', val)
                if match:
                    rating = match.group(1)
                
            # Extract image
            img_el = await item.query_selector('.s-image')
            img_url = await img_el.get_attribute('src') if img_el else ""
            
            # --- Strict Filtering Logic ---
            if is_sponsored:
                filtered_products.append({"id": asin, "title": title, "reviews": reviews_count, "reason": "Sponsored/AD"})
                continue

            if price == "N/A":
                filtered_products.append({"id": asin, "title": title, "reviews": reviews_count, "reason": "Price Missing"})
                continue

            if title and asin:
                organic_products.append(Product(
                    id=asin,
                    url=url,
                    title=title,
                    price=price,
                    rating=rating,
                    reviews_count=reviews_count,
                    image_url=img_url,
                    is_sponsored=False
                ))
        
        print("\n--- ALL ORGANIC CANDIDATES FOUND ---")
        for p in organic_products:
            print(f"ID: {p.id} | Reviews: {p.reviews_count} | Rating: {p.rating} | Title: {p.title[:60]}...")
        print("------------------------------------\n")
        
        # 2. Smart Product Selection: Sort all organic products by reviews_count desc and take top 3
        organic_products.sort(key=lambda x: x.reviews_count or 0, reverse=True)
        top_3 = organic_products[:3]
        
        print(f"Smart-selected top 3 organic products by review count: {[f'{p.id} ({p.reviews_count} reviews, {p.rating} stars)' for p in top_3]}")
        
        # Fetch top reviews and AI summary for these 3 products
        for product in top_3:
            try:
                # Add human-like delay between clicking into different products
                await asyncio.sleep(random.uniform(2.0, 4.0))
                print(f"Deep scraping product page for {product.id}...")
                await page.goto(product.url, wait_until="domcontentloaded")
                await handle_amazon_interstitials(page)
                
                # 1. Scrape Top Individual Reviews
                try:
                    # Amazon.in often uses #cm_cr-review_list or div[data-hook="review"]
                    await page.wait_for_selector('div[data-hook="review"], #cm_cr-review_list', timeout=8000)
                    reviews = await page.query_selector_all('div[data-hook="review"]')
                    if not reviews:
                        reviews = await page.query_selector_all('.review')
                        
                    review_texts = []
                    for rev in reviews[:5]:
                        rev_text_el = await rev.query_selector('span[data-hook="review-body"], .review-text-content')
                        if rev_text_el:
                            review_texts.append(await rev_text_el.inner_text())
                    product.top_reviews = "\n\n".join(review_texts)
                except:
                    product.top_reviews = "No individual reviews found on product page."

                # 2. Scrape Amazon AI Review Summary ("Customers say")
                try:
                    # Amazon often uses #cm-cr-ai-summary or specific hooks
                    ai_summary_el = await page.query_selector('#cm-cr-ai-summary p span')
                    if not ai_summary_el:
                        ai_summary_el = await page.query_selector('[data-hook="customer-review-summary"] p span')
                    if not ai_summary_el:
                        ai_summary_el = await page.query_selector('.cr-summarization-insights span')
                    
                    if not ai_summary_el:
                        # Fallback: look for the heading "Customers say"
                        try:
                            ai_summary_el = await page.query_selector('xpath=//span[contains(text(), "Customers say")]/following::p[1]/span')
                        except:
                            pass
                    
                    if ai_summary_el:
                        product.ai_review_summary = await ai_summary_el.inner_text()
                        print(f"Found AI Summary for {product.id}")
                    else:
                        product.ai_review_summary = "AI Review Summary not available for this product."
                except Exception as e:
                    print(f"Failed to fetch AI summary for {product.id}: {e}")
                    product.ai_review_summary = "AI Review Summary extraction failed."

            except Exception as e:
                print(f"Failed to deep scrape product page for {product.id}: {e}")
                
        await browser.close()
        return top_3, organic_products, filtered_products
