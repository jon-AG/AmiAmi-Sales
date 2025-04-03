import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# === Setup Chrome ===
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def save_debug_page(driver, filename="timeout_debug.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"⚠️ Saved debug HTML to {filename}")

# === Scraping Starts ===
base_search_url = "https://www.amiami.com/eng/search/list/?s_keywords=1/7&s_st_condition_flg=1&s_st_list_newitem_available=1&pagecnt="
base_url = "https://www.amiami.com"
results = []

try:
    print("🔍 Loading first page...")
    driver.get(base_search_url + "1")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CLASS_NAME, "newly-added-items__item__name"))
    )
except TimeoutException:
    print("❌ Timeout while loading page 1.")
    save_debug_page(driver)
    driver.quit()
    exit(1)

soup = BeautifulSoup(driver.page_source, "html.parser")
page_items = soup.find_all("li", class_="pager-list__item pager-list__item_num pconly")
page_numbers = [int(li.text.strip()) for li in page_items if li.text.strip().isdigit()]
total_pages = max(page_numbers) if page_numbers else 1

print(f"✅ Total pages found: {total_pages}")

# === Scrape each page ===
for page in range(1, total_pages + 1):
    print(f"➡️ Scraping page {page} of {total_pages}")
    try:
        driver.get(base_search_url + str(page))
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "newly-added-items__item__name"))
        )
    except TimeoutException:
        print(f"❌ Timeout on page {page}. Saving debug output.")
        save_debug_page(driver, f"timeout_debug_page_{page}.html")
        continue

    soup = BeautifulSoup(driver.page_source, "html.parser")
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

driver.quit()

# === Process results ===
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

# === Save to CSV ===
with open("AmiAmi_sales.csv", "w", encoding="utf-8") as f:
    f.write("Title|Link|Discounted Price|Original Price|Discount\n")
    for item in final_results:
        f.write(f"{item['Title']}|{item['Link']}|{item['Discounted Price']}|{item['Original Price']}|{item['Discount %']}\n")

print("✅ Saved to AmiAmi_sales.csv")

# Print results
for item in final_results:
    print(f"Title: {item['Title']}")
    print(f"Link: {item['Link']}")
    print(f"Discounted Price: {item['Link']}")
    print(f"Original Price:   {item['Original Price']}")
    print(f"Discount:         {item['Discount %']}\n")