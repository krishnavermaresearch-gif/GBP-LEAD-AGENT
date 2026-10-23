from playwright.sync_api import sync_playwright

def test_google_maps_empty():
    url = "https://www.google.com/maps/search/Roofing+Contractors+in+Milak,+Vikas+Nagar,+Sale+Nagar,+loni,+Ghaziabad,+uttar+pradesh,+India"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)
        page.screenshot(path="debug_maps.png")
        print("Screenshot saved to debug_maps.png")
        browser.close()

if __name__ == "__main__":
    test_google_maps_empty()
