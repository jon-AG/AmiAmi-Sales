import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font
from openpyxl.worksheet.hyperlink import Hyperlink

# Setup Chrome options using undetected-chromedriver
options = uc.ChromeOptions()
# Uncomment the following line if you want to try non-headless mode for debugging:
# options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")  # Helps with limited shared memory in GitHub Actions
options.add_argument("--remote-debugging-port=9222")  # Helps stabilize remote debugging connections
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
# Uncomment and adjust the binary location if needed:
# options.binary_location = "/usr/bin/google-chrome-stable"

# Initialize undetected Chrome driver
driver = uc.Chrome(options=options)

# Base search URL
base_search_url = "https://www.amiami.com/eng/search/list/?s_keywords=1/7&s_st_condition_flg=1&s_st_list_newitem_available=1&pagecnt="
# Load first page and wait for product container
driver.get(base_search_url + "1")
WebDriverWait(driver, 60).until(
    EC.presence_of_element_located((By.CLASS_NAME, "newly-added-items__item__name"))
)

# Parse first page to find total number of pages
soup = BeautifulSoup(driver.page_source, "html.parser")
page_items = soup.find_all("li", class_="pager-list__item pager-list__item_num pconly")
page_numbers = []
for li in page_items:
    a_tag = li.find("a", class_="nolink")
    if a_tag and a_tag.text.strip().isdigit():
        page_numbers.append(int(a_tag.text.strip()))
total_pages = max(page_numbers) if page_numbers else 1
print(f"Total pages found: {total_pages}")

# Scrape each page
base_url = "https://www.amiami.com"
results = []
for page in range(1, total_pages + 1):
    print(f"Scraping page {page} of {total_pages}...")
    driver.get(base_search_url + str(page))
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CLASS_NAME, "newly-added-items__item__name"))
    )
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
            if price_tag:
                match = re.search(r"[\d,]+", price_tag.text)
                discounted_price = match.group(0) if match else None
            else:
                discounted_price = None
            original_price = re.search(r"[\d,]+", original_price_tag.text)
            original_price = original_price.group(0) if original_price else None
            if discounted_price and original_price:
                results.append((title, full_link, discounted_price + " JPY", original_price + " JPY"))

driver.quit()

print("\nFinished scraping. Found products:\n")
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
    except:
        continue

header = "Title|Link|Discounted Price|Original Price|Discount\n"
with open("AmiAmi_sales.csv", "w", encoding="utf-8") as f:
    f.write(header)
    for item in final_results:
        f.write(f"{item['Title']}|{item['Link']}|{item['Discounted Price']}|{item['Original Price']}|{item['Discount %']}\n")

for item in final_results:
    print(f"Title: {item['Title']}")
    print(f"Link: {item['Link']}")
    print(f"Discounted Price: {item['Discounted Price']}")
    print(f"Original Price:   {item['Original Price']}")
    print(f"Discount:         {item['Discount %']}\n")

print("Saved to AmiAmi_sales.csv")
