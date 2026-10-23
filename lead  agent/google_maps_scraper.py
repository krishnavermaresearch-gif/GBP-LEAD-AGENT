import time
import re
from playwright.sync_api import sync_playwright
import config

def scrape_google_maps(location, category, limit=None):
    if limit is None:
        limit = config.DEFAULT_LIMIT

    query = f"{category} in {location}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    
    print(f"  🔍 Scraping Google Maps: {url}")
    businesses = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        
        context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
        page = context.new_page()
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_selector('a[href*="/maps/place/"], h1', timeout=15000)
        except Exception as e:
            print(f"  ⚠️  No results found or timed out: {e}")
            browser.close()
            return businesses

        urls = []
        if "/maps/place/" in page.url:
            print("  🎯 Google Maps found exactly 1 perfect match and bypassed the feed!")
            urls.append(page.url)
        else:
            print("  📜 Scrolling Google Maps feed to collect profile links...")
            try:
                page.wait_for_selector('div[role="feed"]', timeout=5000)
                
                previous_count = 0
                retries = 0
                
                while len(urls) < limit and retries < 3:
                    elements = page.query_selector_all('a[href*="/maps/place/"]')
                    
                    for el in elements:
                        url_href = el.get_attribute('href')
                        if url_href and url_href not in urls:
                            urls.append(url_href)
                            
                    count = len(urls)
                    
                    if count == previous_count:
                        retries += 1
                        time.sleep(2)
                    else:
                        retries = 0
                        
                    previous_count = count
                    
                    if elements:
                        elements[-1].scroll_into_view_if_needed()
                        time.sleep(1.5)
                        
                    if page.query_selector("text='You ve reached the end of the list'"):
                        break
                        
            except Exception as e:
                print(f"  ⚠️  Feed scrolling interrupted or none found: {e}")
            
        print(f"  🔗 Collected {len(urls)} profile URLs. Starting Deep Extraction...")

        for i, target_url in enumerate(urls[:limit], start=1):
            try:
                page.goto(target_url, timeout=20000)
                page.wait_for_selector('h1', timeout=10000)
                time.sleep(0.5)
                
                name_loc = page.locator('h1').first
                name = name_loc.inner_text().strip() if name_loc.count() > 0 else "Unknown Name"
                
                rating = "0"
                reviews_count = "0"
                rating_loc = page.locator('div.F7nice').first
                if rating_loc.count() > 0:
                    text = rating_loc.inner_text().replace('\n', '')
                    rank_match = re.search(r'([\d\.]+)\s*\(([\d,]+)\)', text)
                    if rank_match:
                        rating = rank_match.group(1)
                        reviews_count = rank_match.group(2).replace(',', '')
                
                phone = ""
                phone_loc = page.locator('button[data-item-id^="phone:tel:"]').first
                if phone_loc.count() > 0:
                    phone = phone_loc.inner_text().strip()
                else:
                    fallback = page.locator('button[data-tooltip*="phone number" i]').first
                    if fallback.count() > 0:
                        phone = fallback.inner_text().strip()
                        
                website = ""
                web_loc = page.locator('a[data-item-id="authority"]').first
                if web_loc.count() > 0:
                    website = web_loc.get_attribute('href')
                else:
                    web_fallback = page.locator('a[data-tooltip*="Open website" i]').first
                    if web_fallback.count() > 0:
                        website = web_fallback.get_attribute('href')
                        
                address = ""
                addr_loc = page.locator('button[data-item-id="address"]').first
                if addr_loc.count() > 0:
                    address = addr_loc.inner_text().strip()

                businesses.append({
                    "name": name,
                    "rating": rating,
                    "reviews_count": reviews_count,
                    "phone": phone,
                    "address": address,
                    "website": website,
                    "gbp_link": target_url,
                    "raw_text": "",
                    "listing_html": ""
                })
                
            except Exception as e:
                pass

        browser.close()

    print(f"  ✅ Extracted {len(businesses)} deeply-scraped businesses from Google Maps")
    return businesses
