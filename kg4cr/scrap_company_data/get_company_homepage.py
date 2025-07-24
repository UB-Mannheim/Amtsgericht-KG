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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
    
    tlds = ['.com', '.de', '.net', '.org']
    paths = ['', '/en/', '/de/', '/en', '/de']
    variations = []

    for base_name in base_names:
        for tld in tlds:
            for path in paths:
                variations.extend([
                    f"https://www.{base_name}{tld}{path}",
                    f"https://{base_name}{tld}{path}",
                ])

    return list(set(variations))

def test_url(url, timeout=15):
    """Test if a URL is accessible and returns a valid response."""
    try:
        print(f"Testing URL: {url}")
        
        # More comprehensive headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Create a session to handle cookies and maintain state
        session = requests.Session()
        session.headers.update(headers)
        
        # Disable SSL verification if needed (some corporate sites have issues)
        resp = session.get(url, timeout=timeout, allow_redirects=True, verify=True)
        
        print(f"Response status: {resp.status_code} for {url}")
        print(f"Final URL after redirects: {resp.url}")
        print(f"Response headers: {dict(list(resp.headers.items())[:3])}")  # Show first 3 headers
        
        # Check for common blocking indicators
        if resp.status_code == 403:
            print(f"✗ Access forbidden (403) - likely blocked by firewall/security: {url}")
        elif resp.status_code == 503:
            print(f"✗ Service unavailable (503) - might be rate limited: {url}")
        elif 'cloudflare' in resp.text.lower() and resp.status_code != 200:
            print(f"✗ Cloudflare protection detected: {url}")
        elif 'access denied' in resp.text.lower():
            print(f"✗ Access denied in response body: {url}")
        
        if 200 <= resp.status_code < 400:
            # Additional check - make sure we got actual content, not just an error page
            content_length = len(resp.text)
            print(f"✓ URL is valid: {resp.url} (Status: {resp.status_code}, Content length: {content_length})")
            
            # Check if it's a real page or just an error page that returns 200
            if content_length < 100:
                print(f"⚠ Warning: Very short content ({content_length} chars) - might be an error page")
            
            return True, resp.url, resp.status_code
        else:
            print(f"✗ URL returned status {resp.status_code}: {url}")
            return False, None, resp.status_code
            
    except requests.exceptions.SSLError as e:
        print(f"✗ SSL error for URL {url}: {e}")
        # Try again without SSL verification
        try:
            print(f"Retrying {url} without SSL verification...")
            session = requests.Session()
            session.headers.update(headers)
            resp = session.get(url, timeout=timeout, allow_redirects=True, verify=False)
            if 200 <= resp.status_code < 400:
                print(f"✓ URL works without SSL verification: {resp.url} (Status: {resp.status_code})")
                return True, resp.url, resp.status_code
        except Exception as e2:
            print(f"✗ Still failed without SSL verification: {e2}")
        return False, None, None
        
    except requests.exceptions.Timeout:
        print(f"✗ Timeout ({timeout}s) for URL: {url}")
        return False, None, None
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error for URL {url}: {e}")
        return False, None, None
    except requests.RequestException as e:
        print(f"✗ Request exception for URL {url}: {e}")
        return False, None, None
    except Exception as e:
        print(f"✗ Unexpected error for URL {url}: {e}")
        return False, None, None

def handle_cookie_consent(driver, wait_time=10):
    """Enhanced cookie consent handler with multiple strategies."""
    wait = WebDriverWait(driver, wait_time)
    
    # List of common cookie consent selectors and text patterns
    cookie_selectors = [
        # Common button selectors
        "button[id*='accept']",
        "button[class*='accept']",
        "button[id*='cookie']",
        "button[class*='cookie']",
        "button[id*='consent']",
        "button[class*='consent']",
        "button[id*='agree']",
        "button[class*='agree']",
        "button[data-testid*='accept']",
        "button[data-testid*='cookie']",
        "button[data-testid*='consent']",
        "a[id*='accept']",
        "a[class*='accept']",
        "a[id*='cookie']",
        "a[class*='cookie']",
        ".cookie-accept",
        ".accept-cookies",
        ".accept-all",
        "#accept-cookies",
        "#cookie-accept",
        "#accept-all-cookies",
        ".consent-accept",
        ".cookie-consent-accept",
        
        # Common cookie banner frameworks
        ".cc-allow",  # Cookie Consent
        ".cc-dismiss",
        ".optanon-allow-all",  # OneTrust
        ".call-to-action-button",
        ".consent-give",
        ".js-cookie-consent-accept",
        ".gdpr-accept",
        ".privacy-accept",
    ]
    
    # Text patterns for buttons (German and English)
    text_patterns = [
        "akzeptieren", "accept", "agree", "zustimmen", "einverstanden",
        "alle akzeptieren", "accept all", "alle cookies akzeptieren",
        "accept all cookies", "i agree", "ich stimme zu", "verstanden",
        "ok", "got it", "continue", "weiter", "fortfahren", "zulassen",
        "allow", "allow all", "alle zulassen"
    ]
    
    print("Attempting to handle cookie consent...")
    
    # Strategy 1: Try CSS selectors
    for selector in cookie_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    print(f"Found cookie consent button with selector: {selector}")
                    element.click()
                    time.sleep(2)
                    return True
        except Exception as e:
            continue
    
    # Strategy 2: Try XPath with text patterns
    for pattern in text_patterns:
        try:
            # Try button elements first
            xpath_patterns = [
                f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}')]",
                f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}')]",
                f"//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}') and (@role='button' or @onclick)]",
                f"//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern.lower()}') and (parent::button or parent::a)]"
            ]
            
            for xpath in xpath_patterns:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            print(f"Found cookie consent button with text pattern: {pattern}")
                            element.click()
                            time.sleep(2)
                            return True
                except Exception:
                    continue
        except Exception:
            continue
    
    # Strategy 3: Look for common cookie banner containers and find clickable elements within
    banner_selectors = [
        ".cookie-banner", ".cookie-bar", ".cookie-notice", ".cookie-consent",
        ".gdpr-banner", ".privacy-banner", ".consent-banner", "#cookie-banner",
        "#cookie-bar", "#cookie-notice", "[id*='cookie']", "[class*='cookie']",
        "[id*='consent']", "[class*='consent']", "[id*='gdpr']", "[class*='gdpr']"
    ]
    
    for banner_selector in banner_selectors:
        try:
            banners = driver.find_elements(By.CSS_SELECTOR, banner_selector)
            for banner in banners:
                if banner.is_displayed():
                    # Look for clickable elements within the banner
                    clickable_elements = banner.find_elements(By.CSS_SELECTOR, "button, a, [role='button'], [onclick]")
                    for element in clickable_elements:
                        if element.is_displayed() and element.is_enabled():
                            element_text = element.text.lower()
                            if any(pattern in element_text for pattern in text_patterns):
                                print(f"Found cookie consent button in banner: {element_text}")
                                element.click()
                                time.sleep(2)
                                return True
        except Exception:
            continue
    
    # Strategy 4: Look for modal dialogs with cookie consent
    try:
        modals = driver.find_elements(By.CSS_SELECTOR, ".modal, [role='dialog'], [role='alertdialog']")
        for modal in modals:
            if modal.is_displayed():
                modal_text = modal.text.lower()
                if any(keyword in modal_text for keyword in ['cookie', 'consent', 'privacy', 'gdpr', 'datenschutz']):
                    clickable_elements = modal.find_elements(By.CSS_SELECTOR, "button, a, [role='button']")
                    for element in clickable_elements:
                        if element.is_displayed() and element.is_enabled():
                            element_text = element.text.lower()
                            if any(pattern in element_text for pattern in text_patterns):
                                print(f"Found cookie consent button in modal: {element_text}")
                                element.click()
                                time.sleep(2)
                                return True
    except Exception:
        pass
    
    print("No cookie consent popup found or unable to handle it")
    return False

def get_page(url):
    """Get a page using Selenium and handle cookie consent."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(url)
        time.sleep(3)  # Wait for initial page load
        
        # Try to handle cookie consent
        handle_cookie_consent(driver)
        
        # Wait a bit more for any dynamic content to load
        time.sleep(2)
        
        page_html = driver.page_source
        return page_html
    
    except Exception as e:
        print(f"Error loading page {url}: {e}")
        return None
    
    finally:
        driver.quit()

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

def test_url_with_selenium(url, timeout=15):
    """Test URL using Selenium as a fallback when requests fails."""
    print(f"Testing URL with Selenium: {url}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        
        # Wait a moment for the page to load
        time.sleep(3)
        
        current_url = driver.current_url
        title = driver.title
        page_source_length = len(driver.page_source)
        
        print(f"✓ Selenium test successful: {current_url}")
        print(f"  Page title: {title[:100]}...")
        print(f"  Content length: {page_source_length}")
        
        return True, current_url, 200
        
    except Exception as e:
        print(f"✗ Selenium test failed for {url}: {e}")
        return False, None, None
    finally:
        if driver:
            driver.quit()

def find_company_homepage(company_name):
    """Find the homepage of a German company using name variations."""
    print(f"Searching for homepage of: {company_name}")
    
    url_variations = generate_url_variations(company_name)
    print(f"Generated {len(url_variations)} URL variations")
    
    successful_urls = []
    failed_urls = []
    
    for url in url_variations:
        success, final_url, status_code = test_url(url)
        if success:
            successful_urls.append((url, final_url or url, status_code))
            print(f"Found working URL: {final_url}")
        else:
            failed_urls.append(url)
        time.sleep(0.3)
    
    # If no URLs worked with requests, try a few with Selenium
    if not successful_urls and failed_urls:
        print("No URLs worked with requests. Trying top candidates with Selenium...")
        
        # Try the most likely candidates with Selenium
        priority_urls = [url for url in failed_urls if 'www.' in url and '.com' in url][:3]
        
        for url in priority_urls:
            print(f"Selenium fallback test for: {url}")
            success, final_url, status_code = test_url_with_selenium(url)
            if success:
                successful_urls.append((url, final_url or url, status_code))
                print(f"Found working URL via Selenium: {final_url}")
                break
    
    if not successful_urls:
        print("No working URLs found.")
        print("Manual check - trying some common patterns...")
        
        # Manual fallback for common company patterns
        manual_urls = [
            f"https://www.{company_name.lower().replace(' ', '').replace('ag', '').replace('gmbh', '')}.com",
            f"https://www.{company_name.lower().replace(' ', '').replace('ag', '').replace('gmbh', '')}.de",
            f"https://www.{company_name.lower().replace(' ', '').replace('ag', '').replace('gmbh', '')}.com/en/",
            f"https://www.{company_name.lower().replace(' ', '').replace('ag', '').replace('gmbh', '')}.de/en/",
        ]
        
        for url in manual_urls:
            success, final_url, status_code = test_url_with_selenium(url)
            if success:
                successful_urls.append((url, final_url or url, status_code))
                print(f"Found working URL via manual Selenium check: {final_url}")
                break
    
    if not successful_urls:
        print("Still no working URLs found.")
        return None
    
    print(f"Found {len(successful_urls)} valid homepage(s).")
    return successful_urls[0][1]  # Return first valid homepage

def extract_all_links(url):
    """Extract links from a valid homepage."""
    print(f"Extracting links from {url}")
    html = get_page(url)
    
    if html is None:
        print("Failed to get page content")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    links = get_links(soup, url)
    return links

def scrape_company_imprint(company_name, manual_url=None):
    """Find a company's homepage and scrape imprint links."""
    if manual_url:
        print(f"Using manually provided URL: {manual_url}")
        homepage_url = manual_url
        # Verify the manual URL works
        success, final_url, status_code = test_url(manual_url)
        if not success:
            print(f"Manual URL {manual_url} is not accessible")
            return "Manual URL is not accessible."
        homepage_url = final_url or manual_url
    else:
        homepage_url = find_company_homepage(company_name)
        if not homepage_url:
            return "Could not find homepage for the company."
    
    print(f"Found homepage: {homepage_url}")
    links = extract_all_links(homepage_url)
    
    if not links:
        return "Could not extract links from the homepage."
    
    imprint_links = [link for link in links if is_imprint_link(link)]
    
    if imprint_links:
        print(f"Found potential imprint links:")
        for link in imprint_links:
            print(link)
        return imprint_links
    else:
        print("No imprint links found.")
        return []

if __name__ == "__main__":
    company_name = "Bayer AG"  # Example company name
    
    # Option 1: Automatic URL discovery
    scrape_company_imprint(company_name)
    
    # Option 2: Use manual URL if automatic discovery fails
    manual_url = "https://www.bayer.com/en/"
    scrape_company_imprint(company_name, manual_url=manual_url)