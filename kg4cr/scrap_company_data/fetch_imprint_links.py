import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager  # auto installs chromedriver
from selenium.webdriver.common.by import By
from datetime import datetime

def normalize_company_name(company_name):
    """Normalize company name for URL generation."""
    suffixes = ['gmbh', 'ag', 'kg', 'ohg', 'gbr', 'ug', 'eg', 'ev', 'mbh', 'co', '&', 'und']
    normalized = company_name.lower()
    normalized = re.sub(r'[^\w\s-]', '', normalized)
    words = normalized.split()
    filtered_words = [word for word in words if word not in suffixes]
    return ' '.join(filtered_words).strip()

def generate_url_variations(company_name):
    """Generate various URL patterns for company names."""
    normalized = normalize_company_name(company_name)
    base_names = [
        normalized.replace(' ', ''),
        normalized.replace(' ', '-'),
        normalized.replace(' ', '_'),
    ]
    
    if len(normalized.split()) > 1:
        acronym = ''.join(word[0] for word in normalized.split() if word)
        if len(acronym) > 1:
            base_names.append(acronym)
    
    tlds = ['.de', '.com']
    variations = []

    for base_name in base_names:
        for tld in tlds:
            variations.extend([
                f"https://www.{base_name}{tld}",
                f"https://{base_name}{tld}",
                f"http://www.{base_name}{tld}",
                f"http://{base_name}{tld}",
            ])

    return list(set(variations))

def test_url(url, timeout=5):
    """Test if a URL is accessible and returns a valid response."""
    try:
        print(f"Testing URL: {url}")
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        if 200 <= resp.status_code < 400:
            print(f"URL is valid: {resp.url} (Status: {resp.status_code})")
            return True, resp.url, resp.status_code
        return False, None, resp.status_code
    except requests.RequestException:
        return False, None, None

def get_page(url):
    """Get a page using Selenium and handle cookie consent."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.get(url)
    time.sleep(2)
    
    try:
        accept_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Akzeptieren')]")
        accept_button.click()
        time.sleep(3)
    except Exception as e:
        print("No cookie consent found or failed to click:", e)
    
    page_html = driver.page_source
    driver.quit()
    return page_html

def get_links(soup, base_url):
    """Extract all links from soup."""
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        abs_url = urljoin(base_url, href)
        links.add(abs_url)
    return sorted(links)

def is_imprint_link(url, text=None):
    """Check if a URL is likely to contain imprint information."""
    imprint_keywords = ['impressum', 'legal', 'about', 'contact', 'about-us', 'company', 'terms']
    url_lower = url.lower()
    
    for keyword in imprint_keywords:
        if keyword in url_lower:
            return True
    
    if text and any(keyword in text.lower() for keyword in imprint_keywords):
        return True
    return False

def find_company_homepage(company_name):
    """Find the homepage of a German company using name variations."""
    print(f"Searching for homepage of: {company_name}")
    
    url_variations = generate_url_variations(company_name)
    print(f"Generated {len(url_variations)} URL variations:")
    
    successful_urls = []
    for url in url_variations:
        success, final_url, status_code = test_url(url)
        if success:
            successful_urls.append((url, final_url or url, status_code))
        time.sleep(0.5)
    
    if not successful_urls:
        print("No working URLs found.")
        return None
    
    print(f"Found {len(successful_urls)} valid homepage(s).")
    return successful_urls[0][1]  # Return first valid homepage

def extract_all_links(url):
    """Extract links from a valid homepage."""
    print(f"Extracting links from {url}")
    html = get_page(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    links = get_links(soup, url)
    return links

def scrape_company_imprint(company_name):
    """Find a company's homepage and scrape imprint links."""
    homepage_url = find_company_homepage(company_name)
    if not homepage_url:
        return "Could not find homepage for the company."
    
    print(f"Found homepage: {homepage_url}")
    links = extract_all_links(homepage_url)
    
    imprint_links = [link for link in links if is_imprint_link(link)]
    
    if imprint_links:
        print(f"Found potential imprint links:")
        for link in imprint_links:
            print(link)
            return imprint_links
    else:
        print("No imprint links found.")

if __name__ == "__main__":
    company_name = "Bayer AG"  # Example company name
    scrape_company_imprint(company_name)
