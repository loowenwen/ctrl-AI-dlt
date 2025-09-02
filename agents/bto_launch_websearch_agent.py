
import asyncio
import json
from playwright.async_api import async_playwright

URL = "https://homes.hdb.gov.sg/home/finding-a-flat"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=False helps debug
        page = await browser.new_page()

        # Listen to all network responses
        async def handle_response(response):
            try:
                url = response.url
                status = response.status
                print(f"[XHR] URL: {url} | Status: {status}")

                
                if "getCoordinatesByFilters" in url:
                    try:
                        data = await response.json()
                        print("[SUCCESS] Got coordinates data:")
                        print(json.dumps(data, indent=2))
                    except Exception as e_json:
                        print(f"[error] Failed to parse JSON: {e_json}")

            except Exception as e:
                print(f"[error] Handling response: {e}")

        page.on("response", handle_response)

        # Navigate to the page and wait for network activity to finish
        await page.goto(URL, wait_until="networkidle")

        # Optional: wait a few more seconds in case XHR fires later
        await asyncio.sleep(10)

        await browser.close()

asyncio.run(main())
