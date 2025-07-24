import os
import json
import re
from imprint_page_scrapper import extract_full_visible_text, calculate_score, rank_urls_by_score, extract_context_around_patterns
from fetch_imprint_links import scrape_company_imprint
from groq import Groq

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set. Please set it to use the Groq API.")

def extract_register_info(full_text, company_name):
    """
    Use the Groq API to extract the structured information from the provided full text.
    This function assumes that the Groq API is capable of identifying the relevant company registration info.
    """
    client = Groq(api_key=GROQ_API_KEY)

    # Make the API request to extract company registration details
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": f"You're an expert in extracting minute details from the text. You've vast experience in english, modern german as well as old german language. Extract the following information from this text:\n\n"
                    f"Company_Name: {company_name}\n"
                    f"Company_Address: \n"
                    f"Registration Court: \n"
                    f"Registration Code: \n\n"
                    f"Text:\n{full_text}\n\n"
                    f"Please provide the information in JSON format with keys 'Company_Name', 'Company_Address', 'Registration_Court', 'Registration_Code', and 'Registration_year'. Moreover no additional text other than the JSON response should be returned.", 
        }],
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
    )

    # Collect the response content
    extracted_info = ""
    for chunk in completion:
        extracted_info += chunk.choices[0].delta.content or ""

    # Clean the response by removing markdown code blocks if present
    cleaned_response = clean_json_response(extracted_info)
    
    # Assuming the Groq API returns a structured response in JSON format
    try:
        result = json.loads(cleaned_response)  # Convert the extracted info into a JSON object
        return result
    except json.JSONDecodeError:
        print(f"Error decoding Groq response for {company_name}. Raw response: {extracted_info}")
        print(f"Cleaned response: {cleaned_response}")
        return None

def clean_json_response(response):
    """
    Clean the API response by removing markdown code blocks and other formatting.
    """
    # Remove markdown code blocks
    response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
    response = re.sub(r'```\s*$', '', response, flags=re.MULTILINE)
    
    # Remove any leading/trailing whitespace
    response = response.strip()
    
    # Try to extract JSON from the response if it contains other text
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        response = json_match.group(0)
    
    return response

def process_imprint_links(company_name):
    imprint_links = scrape_company_imprint(company_name)
    
    if imprint_links:
        print(f"Found {len(imprint_links)} potential imprint links for {company_name}:")
        for link in imprint_links:
            print(link)
        
        # Rank the URLs and extract full text from the top-ranked one
        ranked_urls = rank_urls_by_score(imprint_links)
        print("\nRanked URLs by score:")
        for url, score in ranked_urls:
            print(f"{url} - Score: {score}")
        
        if ranked_urls:
            top_url = ranked_urls[0][0]
            full_text = extract_full_visible_text(top_url)
            filtered_text = extract_context_around_patterns(full_text)
            print(f"\nFiltered text from top URL ({top_url}):\n{filtered_text}")
            
            # Extract structured data from the filtered text using the Groq API
            register_info = extract_register_info(filtered_text, company_name)
            if register_info:
                return register_info
    
    # print(f"No imprint information found for {company_name}.")
    return {"status": "Not Found", "message": "Imprint info could not be extracted."}

def process_companies(company_names):
    results = {}
    
    for company_name in company_names:
        print(f"\nProcessing {company_name}...")
        register_info = process_imprint_links(company_name)
        
        if register_info:
            if "status" in register_info and register_info["status"] == "Not Found":
                results[company_name] = register_info
            else:
                results[company_name] = register_info
        else:
            results[company_name] = {"status": "Failed", "message": "Error occurred during processing."}
    
    return results

def save_to_json(data, file_name="company_registration_info.json"):
    with open(file_name, 'w') as json_file:
        json.dump(data, json_file, indent=2)
    print(f"Results saved to {file_name}.")

def load_companies_from_file(file_path="companies.txt"):
    """
    Load company names from a text file.
    Each company name should be on a separate line.
    Empty lines and lines starting with # are ignored.
    """
    companies = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    companies.append(line)
        
        print(f"Loaded {len(companies)} companies from {file_path}")
        return companies
    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        print("Please create a companies.txt file with one company name per line.")
        return []
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        return []

def main():
    """
    Main function to process companies from file or use default list.
    """
    # Try to load companies from file first
    company_names = load_companies_from_file("companies.txt")
    
    # If no companies loaded from file, use default list
    if not company_names:
        print("Using default company list...")
        company_names = ["Siemens AG", "Volkswagen AG", "XL2 GmbH", "Rheinmetall AG", "Aleph Alpha GmbH"]
    
    print(f"Processing {len(company_names)} companies:")
    for i, company in enumerate(company_names, 1):
        print(f"{i}. {company}")
    
    # Process all companies
    extracted_results = process_companies(company_names)
    
    # Save results to JSON file
    save_to_json(extracted_results)

# Run the main function
if __name__ == "__main__":
    main()