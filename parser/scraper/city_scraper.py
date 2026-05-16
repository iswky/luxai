from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests
import logging
import time
import re

from pathlib import Path
import sys

# Добавляем корневую директорию
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
try:
    from backend.webui.cities import RUSSIAN_CITIES
except ImportError as e:
    print(f"Import error: {e}")
RUSSIAN_CITIES_SORTED = sorted(RUSSIAN_CITIES, key=len, reverse=True)

from database.db import get_all_from_processing_queue, update_processing_queue_field

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
    """
    Извлекает название города из адреса.
    
    Args:
        address: Строка с адресом
    
   Returns:
        Название города или "Не указан", если город не найден
    """
    if not address or not isinstance(address, str):
        return "Не указан"
    
    address_lower = address.lower()
    
    # Перебираем города от самых длинных к коротким
    # Это нужно, чтобы найти "Ростов-на-Дону", а не просто "Ростов"
    for city in RUSSIAN_CITIES_SORTED:
        city_lower = city.lower()
        
        # Ищем город как отдельное слово в адресе
        # Используем простой поиск подстроки с проверкой границ слов
        if city_lower in address_lower:
            # Проверяем, что это не часть другого слова
            start_idx = address_lower.find(city_lower)
            end_idx = start_idx + len(city_lower)
            
            # Проверяем границы слова
            is_word_boundary = True
            
            if start_idx > 0 and address_lower[start_idx - 1].isalpha():
                is_word_boundary = False
            if end_idx < len(address_lower) and address_lower[end_idx].isalpha():
                is_word_boundary = False
            
            if is_word_boundary:
                return city
    
    return "Не указан"
    

# description: function extract_city. args: html_content. returns: str.
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
            
        city: str = extract_city_from_address(place_of_dispatch)

        return city

    return "Не указан"

def tender_city_parse(tender: dict):
    try:
        full_tender_num = str(tender['tender_number'])
        url = tender['url']

        # originally the xlsx parsing took substring [2:] of the tender_number
        # tender_number in db is stored with a 2-character prefix (see original code reading from cell value)
        tender_num = full_tender_num[2:] if len(full_tender_num) > 2 else full_tender_num
        city: str = tender['city']

        # skip if city is already parsed
        if city and city != 'Не указан':
            return

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
        print(f"Error in tender_city_parse: {e}")


# description: function city_parse. args: . returns: any.
def city_parse():
    try:
        tenders = get_all_from_processing_queue()

        for tender in tenders:
            full_tender_num = tender['tender_number']
            url = tender['url']
            # originally the xlsx parsing took substring [2:] of the tender_number
            # tender_number in db is stored with a 2-character prefix (see original code reading from cell value)
            tender_num = full_tender_num[2:] if len(full_tender_num) > 2 else full_tender_num
            city: str = tender['city']

            # skip if city is already parsed
            if city and city != 'Не указан':
                continue

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