import time
import random
import re
import pandas as pd
import undetected_chromedriver as uc  # use undetected-chromedriver for better stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Setup undetected-chromedriver options
options = uc.ChromeOptions()
options.add_argument("--window-size=1200,1200")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/91.0.4472.124 Safari/537.36")
# You can try enabling headless mode if needed; however, sometimes running in non-headless mode appears more "human"
# options.add_argument("--headless")
options.add_argument("--disable-blink-features=AutomationControlled")
# Additional arguments can be added here as needed

# Initialize undetected-chromedriver (this will automatically try to bypass some detection)
driver = uc.Chrome(options=options)

# Base search URL (using newitem available flag)
base_search_url = "https://www.amiami.com/eng/search/list/?s_keywords=1/7&s_st_condition_flg=1&s_st_list_newitem_available=1&pagecnt="

# Load the first page and wait for the product container
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

# Prepare to collect results
base_url = "https://www.amiami.com"
results = []

# Function to load a page with retry logic
def load_page(url, retries=3, wait_time=60):
    for attempt in range(retries):
        try:
            driver.get(url)
            WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.CLASS_NAME, "newly-added-items__item__name"))
            )
            # Scroll down gradually to simulate human browsing
            for pos in range(0, 1000, 250):
                driver.execute_script(f"window.scrollTo(0, {pos});")
                time.sleep(random.uniform(0.5, 1.0))
            time.sleep(random.uniform(2, 4))
            return True
        except Exception as e:
            print(f"Attempt {attempt+1} failed for URL: {url}. Error: {e}. Retrying in 10 seconds...")
            time.sleep(10)
    return False

# Scrape each page with random delay between pages
for page in range(1, total_pages + 1):
    page_url = base_search_url + str(page)
    print(f"Scraping page {page} of {total_pages}...")
    if not load_page(page_url):
        print(f"Skipping page {page} due to repeated timeouts.")
        continue

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    product_links = soup.find_all("a", href=True)

    for tag in product_links:
        href = tag['href']
        if href.startswith("/eng/detail/?gcode="):
            full_link = base_url + href
            title_tag = tag.find("p", class_="newly-added-items__item__name")
            price_tag = tag.find("p", class_="newly-added-items__item__price")
            original_price_tag = tag.find("span", class_="newly-added-items__item__price_state_discount mleft")

            # Skip if no original price is shown (avoids non-discount items)
            if not original_price_tag:
                continue

            title = title_tag.get_text(strip=True) if title_tag else "No title"
            # Extract discounted price (first number in the price_tag)
            if price_tag:
                match = re.search(r"[\d,]+", price_tag.text)
                discounted_price = match.group(0) if match else None
            else:
                discounted_price = None
            # Extract original price
            original_price = re.search(r"[\d,]+", original_price_tag.text)
            original_price = original_price.group(0) if original_price else None

            if discounted_price and original_price:
                results.append((title, full_link, discounted_price + " JPY", original_price + " JPY"))
    
    # Add a random delay before processing the next page
    time.sleep(random.uniform(3, 6))

driver.quit()

# Process and output final results
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
    except Exception as e:
        print(f"Error processing item '{title}': {e}")
        continue

# Save results to a CSV file with a pipe separator to avoid issues with commas
header = "Title|Link|Discounted Price|Original Price|Discount\n"
with open("AmiAmi_sales.csv", "w", encoding="utf-8") as f:
    f.write(header)
    for item in final_results:
        f.write(f"{item['Title']}|{item['Link']}|{item['Discounted Price']}|{item['Original Price']}|{item['Discount %']}\n")

# Print final results for verification
for item in final_results:
    print(f"Title: {item['Title']}")
    print(f"Link: {item['Link']}")
    print(f"Discounted Price: {item['Discounted Price']}")
    print(f"Original Price:   {item['Original Price']}")
    print(f"Discount:         {item['Discount %']}\n")

print("Saved to AmiAmi_sales.csv")
