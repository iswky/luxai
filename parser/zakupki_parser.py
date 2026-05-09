from typing import Dict, Set, Optional, Any
from bs4 import BeautifulSoup
from datetime import datetime
import traceback
import requests
import time
import csv
import os
import re

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    OPENPYXL_AVAILABLE = True
    print("✅ openpyxl загружен успешно")
except ImportError as e:
    OPENPYXL_AVAILABLE = False
    print(f"❌ openpyxl не установлен: {e}")

class TenderParser:
    """Парсер тендеров с расширенными данными"""

    red_fill: PatternFill
    excel_file: str
    csv_file: str
    headers: Dict[str, str]
    base_url: str
    base_params: Dict[str, str]
    existing_numbers: Set[str]

    def __init__(self, excel_file='tenders.xlsx'):
        self.red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
        self.excel_file = excel_file
        self.csv_file = excel_file.replace('.xlsx', '.csv')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        self.base_url = 'https://zakupki.gov.ru/epz/order/extendedsearch/results.html'
        
        self.base_params = {
            'morphology': 'on',
            'search-filter': 'Дате размещения',
            'sortDirection': 'false',
            'recordsPerPage': '_10',
            'showLotsInfoHidden': 'false',
            'sortBy': 'PUBLISH_DATE',
            'fz44': 'on',
            'fz223': 'on',
            'af': 'on',
            'currencyIdGeneral': '-1',
            'okpd2IdsWithNested': 'on',
            'okpd2Ids': '8873938,8874157,8874056,8873907,8874087,8874160,8874159,8874058,8874059,8874055,8874158,8873937,8873908,8873906,8874054,8874060,8874061',
            'okpd2IdsCodes': '26,26.1,26.2,26.3,26.5,26.7,26.8'
        }
        
        # Загружаем существующие номера при запуске (один раз)
        self.existing_numbers = self.load_existing_tenders()
        
        print("\n" + "="*60)
        print("🎯 ПАРСЕР ЗАПУЩЕН")
        print("="*60)
    
    def load_existing_tenders(self):
        """Загружает существующие номера тендеров из Excel"""
        existing_numbers = set()
        
        if OPENPYXL_AVAILABLE and os.path.exists(self.excel_file):
            try:
                wb = load_workbook(self.excel_file)
                ws = wb.active
                
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row[0]:
                        existing_numbers.add(str(row[0]).strip())
                
                print(f"📂 Загружено существующих тендеров: {len(existing_numbers)}")
            except Exception as e:
                print(f"Ошибка при загрузке: {e}")
        else:
            print("📂 Файл не найден или пуст. Будут добавлены все тендеры.")
        
        return existing_numbers
    
    def save_tenders(self, new_tenders):
        """Сохраняет новые тендеры (только те, которых еще нет)"""
        if not new_tenders:
            return 0
        
        # Фильтруем только новые тендеры
        truly_new = {}
        for number, info in new_tenders.items():
            if number not in self.existing_numbers:
                truly_new[number] = info
                self.existing_numbers.add(number)  # Добавляем в кэш
        
        if not truly_new:
            print(f"⏭️ Нет новых тендеров для сохранения")
            return 0
        
        if OPENPYXL_AVAILABLE:
            result = self._append_to_excel(truly_new)
        else:
            result = self._append_to_csv(truly_new)
        
        return result
    
    def _find_empty_rows(self, ws):
        """
        Находит все пустые строки в таблице.
        Возвращает список номеров строк, где первая колонка пустая.
        """
        empty_rows = []
        max_row = ws.max_row
        
        # Если в таблице только заголовки, нет пустых строк
        if max_row <= 1:
            return []
        
        # Собираем все номера строк с пустой первой колонкой
        for row in range(2, max_row + 1):
            if ws.cell(row=row, column=1).value is None:
                empty_rows.append(row)
            else:
                # Проверяем, не пустая ли строка (все колонки пустые)
                is_completely_empty = True
                for col in range(1, 12):  # Проверяем все 11 колонок
                    if ws.cell(row=row, column=col).value is not None:
                        is_completely_empty = False
                        break
                if is_completely_empty:
                    empty_rows.append(row)
        
        return sorted(empty_rows)  # Сортируем для последовательного заполнения


    def _append_to_excel(self, new_tenders):
        """Добавляет новые тендеры в Excel, заполняя пустые строки в начале"""
        try:
            # Открываем файл
            if os.path.exists(self.excel_file):
                wb = load_workbook(self.excel_file)
                ws = wb.active
            else:
                wb = self._create_excel_file()
                ws = wb.active
            
            # Находим пустые строки
            empty_rows = self._find_empty_rows(ws)
            
            # Создаем очередь из пустых строк
            from collections import deque
            empty_rows_queue = deque(empty_rows)
            
            # Подготавливаем данные для добавления
            added_count = 0
            next_new_row = ws.max_row + 1
            
            for number, info in new_tenders.items():
                # Берем следующую пустую строку или создаем новую
                if empty_rows_queue:
                    target_row = empty_rows_queue.popleft()
                    location = f"пустую строку {target_row}"
                else:
                    target_row = next_new_row
                    next_new_row += 1
                    location = f"новую строку {target_row}"
                
                # Записываем данные
                ws.cell(row=target_row, column=1, value=number)
                ws.cell(row=target_row, column=2, value=info['name'])
                ws.cell(row=target_row, column=3, value=info['url'])
                ws.cell(row=target_row, column=4, value=info.get('price', 'Не указана'))
                ws.cell(row=target_row, column=5, value=info.get('law', 'Не указан'))
                ws.cell(row=target_row, column=6, value=info.get('end_date', 'Не указана'))
                ws.cell(row=target_row, column=7, value=info.get('customer', 'Не указан'))
                ws.cell(row=target_row, column=8, value=info['first_seen'])
                ws.cell(row=target_row, column=9, value=info.get('city', 'Не указан'))
                ws.cell(row=target_row, column=10, value='False')
                ws.cell(row=target_row, column=10).fill = self.red_fill
                ws.cell(row=target_row, column=11, value='False')
                ws.cell(row=target_row, column=11).fill = self.red_fill
                
                added_count += 1
                print(f"   ➕ Тендер {number} добавлен в {location}")
            
            wb.save(self.excel_file)
            print(f"💾 Добавлено {added_count} тендеров (пустых строк использовано: {len(empty_rows[:added_count])})")
            return added_count
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            traceback.print_exc()
            return 0
    
    def _append_to_csv(self, new_tenders):
        """Сохраняет в CSV с колонками Город и Файлы скачаны"""
        try:
            file_exists = os.path.exists(self.csv_file)
            
            with open(self.csv_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if not file_exists:
                    # Заголовки с новыми столбцами
                    writer.writerow(['number', 'name', 'url', 'price', 'law', 'end_date', 
                                    'customer', 'first_seen', 'city', 'files_downloaded'])
                
                for number, info in new_tenders.items():
                    writer.writerow([
                        number, 
                        info['name'], 
                        info['url'],
                        info.get('price', 'Не указана'),
                        info.get('law', 'Не указан'),
                        info.get('end_date', 'Не указана'),
                        info.get('customer', 'Не указан'),
                        info['first_seen'],
                        info.get('city', 'Не указан'),  # Город (пока заглушка, потом можно будет парсить)
                        'False'                         # Файлы скачаны = False
                    ])
            
            print(f"💾 Сохранено {len(new_tenders)} новых тендеров в {self.csv_file}")
            return len(new_tenders)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return 0
    
    def parse_page(self: TenderParser, page_number: int = 1):
        """Парсит страницу"""

        params = self.base_params.copy()
        params['pageNumber'] = str(page_number)
        
        try:
            print(f"📥 Загрузка страницы {page_number}...")
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return self.extract_tenders(soup), soup
        except Exception as e:
            print(f"❌ Ошибка страницы {page_number}: {e}")
            return [], None
    
    def extract_tenders(self, soup):
        """Извлекает тендеры с расширенными данными"""
        tenders = {}
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        blocks = soup.find_all('div', class_='search-registry-entry-block')
        print(f"🔍 Найдено блоков: {len(blocks)}")
        
        for block in blocks:
            try:
                # Номер и ссылка
                number_div = block.find('div', class_='registry-entry__header-mid__number')
                if not number_div:
                    continue
                
                link = number_div.find('a')
                if not link:
                    continue
                
                number = link.text.strip()
                url = 'https://zakupki.gov.ru' + link.get('href')
                
                # Название
                name_div = block.find('div', class_='registry-entry__body-value')
                name = name_div.text.strip() if name_div else 'Название не указано'
                if len(name) > 200:
                    name = name[:197] + '...'
                
                # Заказчик
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
                
                # ФЗ
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
                
                # Цена
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
                
                # Дата окончания
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
                
                # Отмечаем, есть ли уже в базе
                status = "✅" if number not in self.existing_numbers else "⏭️"
                print(f"  {status} {number} | {law} | {price} руб.")
                
            except Exception as e:
                print(f"  ⚠️ Ошибка парсинга блока: {e}")
                continue
        
        return tenders
    
    def has_next_page(self, soup):
        """Проверяет следующую страницу"""
        try:
            return soup.find('a', class_='paginator-button-next') is not None
        except:
            return False
    
    def parse_all_pages(self, max_pages=None):
        """Парсит все страницы и сохраняет по ходу"""
        print("="*60)
        print("🚀 ПАРСИНГ ТЕНДЕРОВ (сохранение по ходу)")
        print("="*60)
        
        page: int = 1
        total_new: int = 0
        
        while True:
            if max_pages and page > max_pages:
                print(f"🏁 Достигнут лимит страниц ({max_pages})")
                break
            
            # self.parse_page(page)


            print(f"\n--- Страница {page} ---")
            
            page_tenders, soup = self.parse_page(page)
            
            if not page_tenders:
                print("❌ Тендеры не найдены")
                break
            
            # Сохраняем ТОЛЬКО НОВЫЕ тендеры с этой страницы
            new_on_page = self.save_tenders(page_tenders)
            total_new += new_on_page
            
            print(f"📊 На странице: новых {new_on_page}, всего добавлено {total_new}")
            
            if not self.has_next_page(soup):
                print("🏁 Последняя страница")
                break
            
            page += 1
            time.sleep(1)  # Пауза между запросами
        
        print(f"\n📊 ВСЕГО ДОБАВЛЕНО НОВЫХ ТЕНДЕРОВ: {total_new}")
        print(f"📁 Всего в базе: {len(self.existing_numbers)}")
        print(f"💾 Файл: {self.excel_file}")
        
        return total_new

def Parse_gos_zakupki():
    parser = TenderParser('tenders.xlsx')

    while True:
        print("\n" + "="*60)
        print("ПАРСЕР ТЕНДЕРОВ (сохранение по ходу)")
        print("="*60)
        print("1. 🚀 Парсить все страницы")
        print("2. 🔢 Парсить N страниц")
        print("3. 🚪 Выход")
        print("="*60)
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            try:
                parser.parse_all_pages()
            except KeyboardInterrupt:
                print("\n\n⚠️ Прервано пользователем")
                print("✅ Данные уже сохранены, можно запустить заново - дубликаты не добавятся")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                traceback.print_exc()
        
        elif choice == '2':
            try:
                pages = input("Сколько страниц парсить? ").strip()
                max_pages = int(pages) if pages else 10
                parser.parse_all_pages(max_pages=max_pages)
            except KeyboardInterrupt:
                print("\n\n⚠️ Прервано пользователем")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        
        elif choice == '3':
            print("👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор")