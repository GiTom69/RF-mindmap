import requests
import json
import string
import time
from bs4 import BeautifulSoup

def scrape_microwaves101():
    """
    Scrapes microwave acronyms from Microwaves101.com for the entire alphabet
    and saves them to a JSON file.
    """
    
    all_acronyms = []
    index_counter = 1
    base_url = "https://www.microwaves101.com/acronyms/microwave-acronyms-"
    alphabet = string.ascii_lowercase
    
    # Using a User-Agent header is good practice for web scraping
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("Starting scraper for Microwaves101 acronyms...")

    # Iterate over each letter from 'a' to 'z'
    for letter in alphabet:
        url = f"{base_url}{letter}"
        print(f"Scraping page: {url}")

        try:
            # Fetch the page content
            response = requests.get(url, headers=headers)
            
            # Check if the page was retrieved successfully
            if response.status_code != 200:
                print(f"  Failed to retrieve page for letter '{letter}'. Status code: {response.status_code}")
                continue # Skip to the next letter

            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the main table containing the acronyms
            # Based on the provided HTML, the table has classes 'table' and 'table-bordered'
            table = soup.find('table', class_='table-bordered')

            if not table:
                print(f"  No acronym table found for letter '{letter}'.")
                continue

            # Find the table body and then all rows (tr) within it
            tbody = table.find('tbody')
            if not tbody:
                print(f"  Table for '{letter}' has no body.")
                continue
                
            rows = tbody.find_all('tr')
            if not rows:
                print(f"  No acronyms (rows) found for letter '{letter}'.")
                continue

            count_for_letter = 0
            # Process each row in the table
            for row in rows:
                # The acronym name is in the table header (th)
                th = row.find('th')
                # The description parts are in the table data (td) cells
                tds = row.find_all('td')

                # Ensure the row structure is as expected (1 <th> and 2 <td>s)
                if th and len(tds) == 2:
                    name = th.get_text(strip=True)
                    desc_part1 = tds[0].get_text(strip=True)
                    desc_part2 = tds[1].get_text(strip=True)

                    # Combine the two description parts as requested
                    description = f"{desc_part1}. {desc_part2}"

                    # Build the dictionary for this acronym
                    acronym_data = {
                        "id": index_counter,
                        "name": name,
                        "description": description,
                        "urls": []
                    }

                    # Add the dictionary to our main list
                    all_acronyms.append(acronym_data)
                    index_counter += 1
                    count_for_letter += 1
            
            print(f"  Found {count_for_letter} acronyms for letter '{letter}'.")

        except requests.exceptions.RequestException as e:
            print(f"  An error occurred while requesting {url}: {e}")
            continue
        
        # Be polite and add a small delay between requests
        time.sleep(0.5)

    # After the loop, save all extracted data to a JSON file
    output_file = 'microwave_acronyms.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Use indent=4 for pretty-printing
            json.dump(all_acronyms, f, indent=4, ensure_ascii=False)
            
        print(f"\nSuccess! Scraped a total of {len(all_acronyms)} acronyms.")
        print(f"Data saved to {output_file}")
        
    except IOError as e:
        print(f"\nError writing to file {output_file}: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during file writing: {e}")

if __name__ == "__main__":
    scrape_microwaves101()