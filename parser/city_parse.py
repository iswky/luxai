from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
import logging
import time
import re

from db import get_all_from_processing_queue, update_processing_queue_field

logging.basicConfig(level = logging.INFO, filename = "parse_logs.log", filemode = "w")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://zakupki.gov.ru/',
    'Connection': 'keep-alive',
}

# pulls city/town name from address
def extract_city_from_address(address: str) -> str:
    
    # city search patterns
    patterns = [
        r'г\.?\s+([А-Яа-я\-]+(?:\s+[А-Яа-я\-]+)?)',  # moscow, moscow
        r'город\s+([А-Яа-я\-]+(?:\s+[А-Яа-я\-]+)?)',  # moscow city
        r'пос\.?\s+([А-Яа-я\-]+(?:\s+[А-Яа-я\-]+)?)',  # villagesolar
        r'д\.?\s+([А-Яа-я\-]+(?:\s+[А-Яа-я\-]+)?)',    # village ivanovka
        r'деревня\s+([А-Яа-я\-]+(?:\s+[А-Яа-я\-]+)?)', # ivanovka village
    ]
    
    for pattern in patterns:
        match = re.search(pattern, address, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # if there are no markers, take the second element by commas
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 2:
        # skip index (first element)
        return parts[1]
    
    return parts[0] if parts else address

def extract_city(html_content: str) -> str:
    soup: BeautifulSoup = BeautifulSoup(html_content, 'html.parser')
    city: str

    sections: List = soup.find_all('section', class_= "blockInfo__section section")

    if not sections:
        print("Section blockInfo__section not found")
        return "Не указан"
    
    print(f"Sections found: {len(sections)}")
    
    for section in sections:
        span = section.find('span', class_ = "section__title")
        
        if not span:
            continue

        if span.get_text(strip = True) != "Место поставки товара, выполнения работы или оказания услуги":
            continue

        span_dispatch = section.find('span', class_ = "section__info")
        if not span_dispatch:
            return "Не указан"

        place_of_dispatch: str = span_dispatch.get_text(strip = True)
        # print(place_of_dispatch)
            
        city: str = extract_city_from_address(place_of_dispatch)
        # print(city)

        return city

    return "Не указан"

def city_parse():
    try:
        tenders = get_all_from_processing_queue()

        for tender in tenders:
            full_tender_num = tender['tender_number']
            # originally the xlsx parsing took substring [2:] of the tender_number
            # tender_number in db is stored with a 2-character prefix (see original code reading from cell value)
            tender_num = full_tender_num[2:] if len(full_tender_num) > 2 else full_tender_num
            city: str = tender['city']

            # skip if city is already parsed
            if city and city != 'Не указан':
                continue

            url = 'https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=' + tender_num

            try:
                response = requests.get(url, headers = headers, timeout=15)
                html_text: str = response.text
                new_city = extract_city(html_text)

                update_processing_queue_field(full_tender_num, 'city', new_city)
                print(f"Updated city for {full_tender_num}: {new_city}")

                time.sleep(1)
            except Exception as req_err:
                print(f"Error fetching city for {full_tender_num}: {req_err}")
    except Exception as e:
        print(f"Error in city_parse: {e}")