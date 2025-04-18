import re
import asyncio
import random
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import sys

# === Config ===
base_search_url = "https://www.amiami.com/eng/search/list/?s_keywords=1/7&s_st_condition_flg=1&s_st_list_newitem_available=1&pagecnt="
base_url = "https://www.amiami.com"

async def scrape():
    results = []
    print("🔍 Launching browser...")
    async with async_playwright() as p:
        # Launch in headless mode; if you experience issues, try running non-headless for debugging.
        browser = await p.chromium.launch(headless=True)
        # Set a standard desktop viewport for realistic page rendering.
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        # Inject stealth script to mask automation fingerprints
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        print("🔍 Loading first page with stealth...")
        await page.goto(base_search_url + "1")
        # Wait a random amount between 3 and 5 seconds
        await page.wait_for_timeout(random.randint(3000, 5000))
        content = await page.content()
        print(content[:3000])  # Debug: print first 3000 chars
        soup = BeautifulSoup(content, "html.parser")

        # Find all <li> elements with page numbers
        page_items = soup.find_all("li", class_="pager-list__item pager-list__item_num pconly")
        page_numbers = [int(li.text.strip()) for li in page_items if li.text.strip().isdigit()]
        total_pages = max(page_numbers) if page_numbers else 1
        print(f"✅ Total pages found: {total_pages}")
        # Optional: temporarily reduce pages for testing
        # total_pages = 1

        for page_num in range(1, total_pages + 1):
            print(f"➡️ Scraping page {page_num} of {total_pages}")
            try:
                await page.goto(base_search_url + str(page_num))
            except Exception as e:
                print(f"⚠️ Error loading page {page_num}: {e}")
                continue

            await page.wait_for_timeout(random.randint(3000, 5000))
            # Scroll to the bottom to trigger lazy loading (if any)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(random.randint(3000, 5000))
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            product_links = soup.find_all("a", href=True)

            for tag in product_links:
                href = tag['href']
                if href.startswith("/eng/detail/?gcode="):
                    full_link = base_url + href
                    gcode_match = re.search(r"gcode=([A-Z0-9\-]+)", href)
                    gcode = gcode_match.group(1) if gcode_match else ""

                    title_tag = tag.find("p", class_="newly-added-items__item__name")
                    price_tag = tag.find("p", class_="newly-added-items__item__price")
                    original_price_tag = tag.find("span", class_="newly-added-items__item__price_state_discount mleft")

                    product_container = tag.find_parent("li", class_="newly-added-items__item")
                    condition = "New"
                    img_url = ""
                    if product_container:
                        # Extract image URL
                        img_tag = product_container.find("img")
                        if img_tag and "src" in img_tag.attrs:
                            img_url = img_tag["src"]
                        # Determine status from tag list
                        status_ul = product_container.find("ul", class_="newly-added-items__item__tag-list")
                        if status_ul:
                            for li in status_ul.find_all("li"):
                                style = li.get("style", "")
                                if "display: none" not in style:
                                    condition = li.get_text(strip=True)
                                    break

                    # If no proper image URL or original price tag, skip
                    if not img_url.startswith("http") or not original_price_tag:
                        continue

                    title = title_tag.get_text(strip=True) if title_tag else "No title"
                    match = re.search(r"[\d,]+", price_tag.text) if price_tag else None
                    discounted_price = match.group(0) if match else None
                    original_match = re.search(r"[\d,]+", original_price_tag.text)
                    original_price = original_match.group(0) if original_match else None

                    if discounted_price and original_price:
                        results.append((condition, title, full_link, discounted_price + " JPY", original_price + " JPY", img_url))

        await browser.close()
    return results

async def main():
    results = await scrape()
    print(f"\n📦 Finished scraping. Total products found: {len(results)}")
    if len(results) == 0:
        sys.exit("🚨 No products found; likely blocked or challenge page returned.")

    final_results = []
    for condition, title, link, discounted_str, original_str, img_url in results:
        try:
            discounted = int(discounted_str.replace(" JPY", "").replace(",", ""))
            original = int(original_str.replace(" JPY", "").replace(",", ""))
            discount_percent = round((original - discounted) / original * 100, 2)
            final_results.append({
                "Condition": condition,
                "Title": title,
                "Link": link,
                "Image": img_url,
                "Discounted Price": f"{discounted:,} JPY",
                "Original Price": f"{original:,} JPY",
                "Discount %": f"{discount_percent}%"
            })
        except Exception as e:
            print(f"⚠️ Error processing item '{title}': {e}")
            continue

    # Sort by discount descending
    final_results.sort(key=lambda x: float(x["Discount %"].replace("%", "")), reverse=True)

    # Save to CSV (pipe-separated to avoid comma issues)
    with open("AmiAmi_sales.csv", "w", encoding="utf-8") as f:
        f.write("Condition|Title|Link|Discounted Price|Original Price|Discount|Image\n")
        for item in final_results:
            f.write(f"{item['Condition']}|{item['Title']}|{item['Link']}|{item['Discounted Price']}|{item['Original Price']}|{item['Discount %']}|{item['Image']}\n")
    print("✅ Saved to AmiAmi_sales.csv")

    # Save to Markdown (for GitHub preview)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("### 📦 AmiAmi Discounted Figures\n\n")
        f.write("| Condition | Pic | Title | Discounted Price | Original Price | Discount | Link |\n")
        f.write("|-----------|-----|-------|------------------|----------------|----------|------|\n")
        for item in final_results:
            f.write(f"| {item['Condition']} | ![]({item['Image']}) | {item['Title']} | {item['Discounted Price']} | {item['Original Price']} | {item['Discount %']} | [Link]({item['Link']}) |\n")
    print("✅ Saved to README.md")

    # Save to Excel
    df = pd.DataFrame(final_results)
    excel_filename = "AmiAmi_sales.xlsx"
    with pd.ExcelWriter(excel_filename, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]
        worksheet.autofilter(0, 0, len(df.index), len(df.columns) - 1)
        title_format = workbook.add_format({"text_wrap": True})
        for i, col in enumerate(df.columns):
            if col == "Title":
                worksheet.set_column(i, i, 50, title_format)
            else:
                column_data = df[col].astype(str)
                max_len = max(column_data.map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_len)
    print(f"✅ Saved to {excel_filename}")

    for item in final_results:
        print(f"Condition:       {item['Condition']}")
        print(f"Title:           {item['Title']}")
        print(f"Link:            {item['Link']}")
        print(f"Image:           {item['Image']}")
        print(f"Discounted Price:{item['Discounted Price']}")
        print(f"Original Price:  {item['Original Price']}")
        print(f"Discount:        {item['Discount %']}\n")

if __name__ == "__main__":
    asyncio.run(main())
