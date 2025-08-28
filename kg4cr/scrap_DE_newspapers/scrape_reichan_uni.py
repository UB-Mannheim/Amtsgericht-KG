from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

CHROMEDRIVER_PATH = r"/mnt/c/Users/abhijain/Documents/KG4CR/kg4cr/scrap_DE_newspapers/chromedriver.exe"
service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service)
driver.get("https://digi.bib.uni-mannheim.de/periodika/reichsanzeiger/suche/")

# Step 1: Search for 'amtsgericht'
search_input = WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.TAG_NAME, "input"))
)
search_input.clear()
search_input.send_keys("amtsgericht")
search_input.send_keys(Keys.RETURN)

all_result_urls = set()
page_num = 1

while True:
    # Step 2: Wait for results to load
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "searchResultList"))
    )
    results = driver.find_elements(By.CSS_SELECTOR, "#searchResultList > li")
    for li in results:
        try:
            url = li.find_element(By.CSS_SELECTOR, "h3.title a.link").get_attribute("href")
            if url:
                all_result_urls.add(url)
        except Exception:
            continue
    print(f"Page {page_num}: {len(results)} links collected, total: {len(all_result_urls)}")

    # Step 3: Find and click "next" page button, or break if it's the last page
    try:
        pagination = driver.find_element(By.CSS_SELECTOR, "ul.pagination")
        next_btn = pagination.find_element(By.XPATH, './/li[a and (a[text()="»"] or a[@aria-label="Next"])]')
        # Check if "next" is disabled
        if 'disabled' in next_btn.get_attribute("class"):
            break
        next_btn.find_element(By.TAG_NAME, "a").click()
        page_num += 1
        time.sleep(1.5)
    except Exception:
        # No more pages
        break

driver.quit()

print("\nAll result links collected:")
for idx, url in enumerate(sorted(all_result_urls), 1):
    print(f"{idx}: {url}")