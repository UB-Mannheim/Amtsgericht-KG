import re
from playwright.sync_api import sync_playwright

def extract_full_visible_text(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(7000)  # Wait 7 seconds to ensure full JS render

        # Use JS to get fully rendered visible text (includes content from shadow DOMs)
        full_text = page.evaluate("""() => {
            function getTextFromNode(node) {
                let text = '';
                if (node.nodeType === Node.TEXT_NODE) {
                    return node.textContent.trim();
                }
                if (node.shadowRoot) {
                    for (let child of node.shadowRoot.childNodes) {
                        text += getTextFromNode(child) + '\\n';
                    }
                }
                for (let child of node.childNodes) {
                    text += getTextFromNode(child) + '\\n';
                }
                return text;
            }
            return getTextFromNode(document.body);
        }""")

        browser.close()

        return full_text

def extract_context_around_patterns(full_text):
    """Extract 500 chars before and after the first matched pattern."""
    
    # Define the patterns you want to match in order
    registration_court_keywords = r"(Amtsgericht|Registration\sCourt|Handelsregister|Registergericht)"
    
    # Combine all patterns into one pattern
    combined_pattern = f"({registration_court_keywords})"
    
    # Compile the pattern to perform the search
    pattern = re.compile(combined_pattern)
    
    # Find the first match of the pattern
    match = pattern.search(full_text)
    
    if match:
        # Get the matched string
        matched_text = match.group(0)
        
        # Get the start and end positions of the match
        start_idx = match.start()
        end_idx = match.end()
        
        # Extract 500 characters before and after the matched text
        start_extract = max(start_idx - 500, 0)  # Ensure we don't go negative
        end_extract = min(end_idx + 500, len(full_text))  # Ensure we don't go beyond text
        
        # Get the surrounding context
        context = full_text[start_extract:end_extract]
        
        # Return the result as a tuple (start, matched_text, context)
        return [(start_idx, matched_text, context)]
    
    # If no match is found, return an empty list
    return []


def calculate_score(text):
    score = 0
    
    # Define the regex patterns for different categories
    address_keywords = r"(Adresse|Impressum|Company\sAddress|Registered\sOffice)"
    registration_court_keywords = r"(Amtsgericht|Registration\sCourt|Handelsregister|Registergericht)"
    registration_pattern = r"(HRB|HRA|VR|GnR|PartR|HRB\sEWR|WR|GeR)\s?\d{1,5}"

    # Check for address-related info
    if re.search(address_keywords, text, re.IGNORECASE):
        score += 1  # Add 1 point for address-related info

    # Check for registration court-related info
    if re.search(registration_court_keywords, text, re.IGNORECASE):
        score += 1  # Add 1 point for registration court-related info

    # Check for register number-related info
    if re.search(registration_pattern, text):
        score += 1  # Add 1 point for registration number info

    return score

def rank_urls_by_score(urls):
    url_scores = []

    for url in urls:
        # Extract the full visible text from the URL
        print(f"Processing URL: {url}")
        full_text = extract_full_visible_text(url)

        # Calculate the score based on the extracted text
        score = calculate_score(full_text)

        # Add the URL and its score to the list
        url_scores.append((url, score))

    # Sort the URLs based on their scores in descending order (higher score = more relevant)
    url_scores.sort(key=lambda x: x[1], reverse=True)

    # Return the URLs ordered by score
    return url_scores

if __name__ == "__main__":
    # Example usage
    urls = [
        "https://www.volkswagen.de/de/mehr/impressum.html",
        "https://example.com/other-page",
        "https://www.bmw.de/de/unternehmen/impressum.html",
        "https://www.volkswagen.de/de.html",
        "https://www.siemens.com/de/de/general/legal.html"
        # Add more URLs to check
    ]

    ranked_urls = rank_urls_by_score(urls)

    # Display the ranked URLs
    print("\nRanked URLs based on relevance:")
    for url, score in ranked_urls:
        print(f"{url} (Score: {score})")
        print("Context around patterns:")
        context_results = extract_context_around_patterns(extract_full_visible_text(url))
        for start_idx, matched_text, context in context_results:
            print(f"Matched: '{matched_text}' at index {start_idx}")
            print(f"Context: {context}\n")
