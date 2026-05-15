from typing import Dict, Set, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime
import traceback
import requests
import time
import csv
import os
import re

from database.db import get_existing_queue_numbers, add_to_processing_queue, ensure_processing_queue_table

# tender parser with extended data
class TenderParser:

    headers: Dict[str, str]
    base_url: str
    base_params: Dict[str, str]
    existing_numbers: Set[str]

# description: function __init__. args: self. returns: any.
    def __init__(self):
        ensure_processing_queue_table()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        self.base_url = 'https://zakupki.gov.ru/epz/order/extendedsearch/results.html'
        
        self.base_params = self.load_filters_from_file("./params.txt")
        
        # load existing numbers at startup (one time)
        self.existing_numbers = self.load_existing_tenders()
        
        print("\n" + "="*60)
        print("PARSER STARTED")
        print("="*60)
    
    # reads filters from a txt file in the key=value format
    def load_filters_from_file(self, file_path: str) -> Dict[str, str]:
        params: Dict[str, str] = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # divide by the first equal sign
                    if '=' in line:
                        key, value = line.split('=', 1)
                        params[key.strip()] = value.strip()
                        
        except FileNotFoundError:
            print(f"File {file_path} not found")
        except Exception as e:
            print(f"Error reading file: {e}")
        
        return params

    # grabs existing tender numbers from db
    def load_existing_tenders(self):
        try:
            existing_numbers = get_existing_queue_numbers()
            print(f"Existing tenders loaded: {len(existing_numbers)}")
            return existing_numbers
        except Exception as e:
            print(f"Error loading existing tenders: {e}")
            return set()
    
    # stashes new tenders in db (only those that don't exist yet)
    def save_tenders(self, new_tenders):
        if not new_tenders:
            return 0
        
        # we filter only new tenders
        truly_new = {}
        for number, info in new_tenders.items():
            if number not in self.existing_numbers:
                truly_new[number] = info
                self.existing_numbers.add(number)  # add to cache
        
        if not truly_new:
            print(f"No new tenders to save")
            return 0
        
        added_count = add_to_processing_queue(truly_new)
        print(f"Added {added_count} tenders to database")
        return added_count
    
    # chews through the page
    def parse_page(self, page_number: int = 1):

        # params = self.base_params.copy()
        params: Dict[str, str] = {}
        params['pageNumber'] = str(page_number)
        
        url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html?morphology=on&search-filter=%D0%94%D0%B0%D1%82%D0%B5+%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D1%8F&sortDirection=false&recordsPerPage=_10&showLotsInfoHidden=false&sortBy=UPDATE_DATE&fz44=on&fz223=on&af=on&currencyIdGeneral=-1&okpd2Ids=8889332%2C8889331%2C8873906&okpd2IdsCodes=32.99.53.190%2C32.99.53.130%2C26"

        try:
            print(f"Loading page {page_number}...")
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return self.extract_tenders(soup), soup
        except Exception as e:
            print(f"Page error {page_number}: {e}")
            return [], None
    
    # retrieves tenders with enhanced data
    def extract_tenders(self, soup):
        tenders = {}
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        blocks = soup.find_all('div', class_='search-registry-entry-block')
        print(f"Blocks found: {len(blocks)}")
        
        for block in blocks:
            try:
                # number and link
                number_div = block.find('div', class_='registry-entry__header-mid__number')
                if not number_div:
                    continue
                
                link = number_div.find('a')
                if not link:
                    continue
                
                number = link.text.strip()
                url = link.get('href')
                
                # name
                name_div = block.find('div', class_='registry-entry__body-value')
                name = name_div.text.strip() if name_div else 'Название не указано'
                if len(name) > 200:
                    name = name[:197] + '...'
                
                # customer
                customer = 'Не указан'
                customer_block = block.find('div', class_='registry-entry__body-block')
                if customer_block:
                    customer_title = customer_block.find('div', class_='registry-entry__body-title', string=re.compile(r'Заказчик|Организация'))
                    if customer_title:
                        customer_value = customer_title.find_next_sibling('div', class_='registry-entry__body-href')
                        if not customer_value:
                            customer_value = customer_title.find_next_sibling('div', class_='registry-entry__body-value')
                        if customer_value:
                            customer = customer_value.text.strip()
                            if len(customer) > 100:
                                customer = customer[:97] + '...'
                    else:
                        body_href = block.find('div', class_='registry-entry__body-href')
                        if body_href:
                            customer = body_href.text.strip()
                            if len(customer) > 100:
                                customer = customer[:97] + '...'
                
                # federal law
                law_tag = block.find('div', class_='registry-entry__header-top__title')
                law = 'Не указан'
                if law_tag:
                    law_text = law_tag.text.strip()
                    if '44-ФЗ' in law_text:
                        law = '44-ФЗ'
                    elif '223-ФЗ' in law_text:
                        law = '223-ФЗ'
                    else:
                        law = law_text[:20]
                
                # price
                price = 'Не указана'
                price_block = block.find('div', class_='price-block')
                if price_block:
                    price_value = price_block.find('div', class_='price-block__value')
                    if price_value:
                        price_text = price_value.text.strip()
                        price_match = re.search(r'([\d\s]+[\.,]\d{2})', price_text)
                        if price_match:
                            price = price_match.group(1).replace(' ', '').replace(',', '.')
                        else:
                            price = price_text.replace('₽', '').replace('&8381;', '').strip()
                
                # end date
                end_date = 'Не указана'
                data_block = block.find('div', class_='data-block')
                if data_block:
                    titles = data_block.find_all('div', class_='data-block__title')
                    values = data_block.find_all('div', class_='data-block__value')
                    for i, title in enumerate(titles):
                        if 'окончание' in title.text.lower() or 'подачи' in title.text.lower():
                            if i < len(values):
                                end_date = values[i].text.strip()
                                break
                
                tenders[number] = {
                    'name': name,
                    'url': url,
                    'price': price,
                    'law': law,
                    'end_date': end_date,
                    'customer': customer,
                    'first_seen': current_date
                }
                
                # we note whether it is already in the database
                status = "New" if number not in self.existing_numbers else "Exists"
                print(f"{status} {number} | {law} | {price} rub.")
                
            except Exception as e:
                print(f"Block parsing error: {e}")
                continue
        
        return tenders
    
    # peeks at next page
    def has_next_page(self, soup):
        try:
            return soup.find('a', class_='paginator-button-next') is not None
        except:
            return False
    
    # chews through all pages and stashes along the way
    def parse_all_pages(self, max_pages=None, page_callback=None):
        print("="*60)
        print("PARSING TENDERS (saving as we go)")
        print("="*60)
        
        page: int = 1
        total_new: int = 0
        
        while True:
            if max_pages and page > max_pages:
                print(f"Page limit reached ({max_pages})")
                break
            
            print(f"\n--- Page {page} ---")
            
            page_tenders, soup = self.parse_page(page)
            
            if not page_tenders:
                print("Tenders not found")
                break
            
            # we save only new tenders from this page
            new_on_page = self.save_tenders(page_tenders)
            total_new += new_on_page
            
            print(f"On page: new {new_on_page}, total added {total_new}")
            
            if page_callback:
                print("Running callback for processed page")
                page_callback()

            if not self.has_next_page(soup):
                print("Last page")
                break
            
            page += 1
            time.sleep(1)  # pause between requests
        
        print(f"\n TOTAL NEW TENDERS ADDED: {total_new}")
        print(f"Total in database: {len(self.existing_numbers)}")
        
        return total_new

# description: function Parse_gos_zakupki. args: interactive, page_callback. returns: any.
def Parse_gos_zakupki(interactive=True, page_callback=None):
    parser = TenderParser()

    if not interactive:
        try:
            parser.parse_all_pages(page_callback=page_callback)
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
        return

    while True:
        print("\n" + "="*60)
        print("TENDER PARSER (saving as we go)")
        print("="*60)
        print("1.  Parse all pages")
        print("2.  Parse N pages")
        print("3.  Exit")
        print("="*60)
        
        choice = input("Choose an action: ").strip()
        
        if choice == '1':
            try:
                parser.parse_all_pages(page_callback=page_callback)
            except KeyboardInterrupt:
                print("\n\n Interrupted by user")
                print("Data already saved, can restart - duplicates will not be added")
            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()
        
        elif choice == '2':
            try:
                pages = input("How many pages to parse? ").strip()
                max_pages = int(pages) if pages else 10
                parser.parse_all_pages(max_pages=max_pages, page_callback=page_callback)
            except KeyboardInterrupt:
                print("\n\n Interrupted by user")
            except Exception as e:
                print(f"Error: {e}")
        
        elif choice == '3':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice")

if __name__ == "__main__":
    


    Parse_gos_zakupki()