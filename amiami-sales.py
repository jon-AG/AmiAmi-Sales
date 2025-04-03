import re
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# === Config ===
base_search_url = "https://www.amiami.com/eng/search/list/?s_keywords=1/7&s_st_condition_flg=1&s_st_list_newitem_available=1&pagecnt="
base_url = "https://www.amiami.com"

async def scrape():
    results = []
    print("🔍 Launching browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = await context.new_page()

        print("🔍 Loading first page...")
        await page.goto(base_search_url + "1")
        await page.wait_for_timeout(3000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        page_items = soup.find_all("li", class_="pager-list__item pager-list__item_num pconly")
        page_numbers = [int(li.text.strip()) for li in page_items if li.text.strip().isdigit()]
        total_pages = max(page_numbers) if page_numbers else 1
        total_pages = 1

        print(f"✅ Total pages found: {total_pages}")

        for page_num in range(1, total_pages + 1):
            print(f"➡️ Scraping page {page_num} of {total_pages}")
            await page.goto(base_search_url + str(page_num))
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            product_links = soup.find_all("a", href=True)

            for tag in product_links:
                href = tag['href']
                if href.startswith("/eng/detail/?gcode="):
                    full_link = base_url + href
                    title_tag = tag.find("p", class_="newly-added-items__item__name")
                    price_tag = tag.find("p", class_="newly-added-items__item__price")
                    original_price_tag = tag.find("span", class_="newly-added-items__item__price_state_discount mleft")

                    if not original_price_tag:
                        continue

                    title = title_tag.get_text(strip=True) if title_tag else "No title"
                    match = re.search(r"[\d,]+", price_tag.text) if price_tag else None
                    discounted_price = match.group(0) if match else None
                    original_match = re.search(r"[\d,]+", original_price_tag.text)
                    original_price = original_match.group(0) if original_match else None

                    if discounted_price and original_price:
                        results.append((title, full_link, discounted_price + " JPY", original_price + " JPY"))

        await browser.close()
    return results

async def main():
    results = await scrape()
    print(f"\n📦 Finished scraping. Total products found: {len(results)}")

    final_results = []
    for title, link, discounted_str, original_str in results:
        try:
            discounted = int(discounted_str.replace(" JPY", "").replace(",", ""))
            original = int(original_str.replace(" JPY", "").replace(",", ""))
            discount_percent = round((original - discounted) / original * 100, 2)
            final_results.append({
                "Title": title,
                "Link": link,
                "Discounted Price": f"{discounted:,} JPY",
                "Original Price": f"{original:,} JPY",
                "Discount %": f"{discount_percent}%"
            })
        except Exception as e:
            print(f"⚠️ Error processing item '{title}': {e}")
            continue

    # Save to CSV
    with open("AmiAmi_sales.csv", "w", encoding="utf-8") as f:
        f.write("Title|Link|Discounted Price|Original Price|Discount\n")
        for item in final_results:
            f.write(f"{item['Title']}|{item['Link']}|{item['Discounted Price']}|{item['Original Price']}|{item['Discount %']}\n")
    print("✅ Saved to AmiAmi_sales.csv")

    # Save to Markdown
    with open("AmiAmi_sales.md", "w", encoding="utf-8") as f:
        f.write("### 📦 AmiAmi Discounted Figures\n\n")
        f.write("| Title | Discounted Price | Original Price | Discount | Link |\n")
        f.write("|-------|------------------|----------------|----------|------|\n")
        for item in final_results:
            f.write(f"| {item['Title']} | {item['Discounted Price']} | {item['Original Price']} | {item['Discount %']} | [Link]({item['Link']}) |\n")
    print("✅ Saved to AmiAmi_sales.md")

    # Optional print preview
    for item in final_results:
        print(f"Title: {item['Title']}")
        print(f"Link: {item['Link']}")
        print(f"Discounted Price: {item['Discounted Price']}")
        print(f"Original Price:   {item['Original Price']}")
        print(f"Discount:         {item['Discount %']}\n")

if __name__ == "__main__":
    asyncio.run(main())
