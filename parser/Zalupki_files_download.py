import requests
from bs4 import BeautifulSoup
import os
import re
import zipfile
from urllib.parse import urljoin
import time
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

class TenderFilesDownloader:
    """Скачивает файлы и парсит город для тендеров из Excel"""
    
    def __init__(self, excel_file='tenders.xlsx'):
        self.excel_file = excel_file
        self.base_url = 'https://zakupki.gov.ru'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        self.red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
        self.green_fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
    
    def clean_tender_number(self, raw_number):
        """Очищает номер тендера от лишних символов"""
        if not raw_number:
            return None
        
        # Преобразуем в строку
        number_str = str(raw_number).strip()
        
        # Удаляем символ № и другие нецифровые символы, оставляем только цифры и дефисы
        # Но формат номера: 0338100001126000014 (цифры)
        cleaned = re.sub(r'[^0-9]', '', number_str)
        
        # Если после очистки ничего не осталось - пробуем другие методы
        if not cleaned:
            # Убираем только символ № и пробелы
            cleaned = number_str.replace('№', '').replace(' ', '').strip()
        
        print(f"   Очистка номера: '{raw_number}' -> '{cleaned}'")
        return cleaned
    
    def parse_city(self, tender_number):
        """Парсит город из страницы common-info"""
        # Очищаем номер
        clean_number = self.clean_tender_number(tender_number)
        if not clean_number:
            return 'Ошибка номера'
        
        url = f'https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber={clean_number}'
        
        try:
            print(f"  🌍 Загрузка страницы для определения города...")
            print(f"  🔗 URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем регион/город
            city = self._extract_city_from_soup(soup)
            print(f"  📍 Город: {city}")
            return city
            
        except Exception as e:
            print(f"  ❌ Ошибка при парсинге города: {e}")
            return 'Ошибка'
    
    def _extract_city_from_soup(self, soup):
        """Извлекает город из BeautifulSoup объекта"""
        # Способ 1: ищем секцию "Регион"
        region_section = soup.find('section', class_='blockInfo__section')
        if region_section:
            # Ищем заголовок "Регион"
            for span in region_section.find_all('span', class_='section__title'):
                if span.text and 'Регион' in span.text:
                    value_span = span.find_next_sibling('span', class_='section__info')
                    if value_span and value_span.text:
                        return value_span.text.strip()
        
        # Способ 2: ищем "Регион" в тексте
        page_text = soup.get_text()
        match = re.search(r'Регион\s*([А-Яа-я\-\s]+?)(?:\n|$)', page_text)
        if match:
            return match.group(1).strip()
        
        # Способ 3: ищем "Почтовый адрес" или "Место нахождения"
        for title_text in ['Почтовый адрес', 'Место нахождения']:
            for span in soup.find_all('span', class_='section__title'):
                if span.text and title_text in span.text:
                    value_span = span.find_next_sibling('span', class_='section__info')
                    if value_span and value_span.text:
                        address = value_span.text.strip()
                        # Извлекаем город из адреса
                        city_match = re.search(r'(?:г\.|город)\s*([А-Яа-я\-]+)', address)
                        if city_match:
                            return city_match.group(1)
        
        return 'Не указан'
    
    def download_files(self, tender_number):
        """Скачивает все файлы со страницы documents"""
        # Очищаем номер
        clean_number = self.clean_tender_number(tender_number)
        if not clean_number:
            return 0
        
        # Создаем папку для тендера
        tender_dir = os.path.join('tenders_files', clean_number)
        os.makedirs(tender_dir, exist_ok=True)
        
        url = f'https://zakupki.gov.ru/epz/order/notice/ea20/view/documents.html?regNumber={clean_number}'
        
        try:
            print(f"  📄 Загрузка страницы документов...")
            print(f"  🔗 URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 404:
                print(f"  ⚠️ Страница не найдена (404) для номера {clean_number}")
                return 0
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем блок с файлами
            files_block = soup.find('div', class_='blockFilesTabDocs')
            if not files_block:
                print(f"  ⚠️ Блок с файлами не найден")
                return 0
            
            # Ищем все ссылки на файлы
            file_links = files_block.find_all('a', href=True)
            downloaded_count = 0
            
            for link in file_links:
                href = link.get('href', '')
                # Ищем ссылки на скачивание файлов
                if '/44fz/filestore/public/1.0/download/priz/file.html' in href:
                    file_url = urljoin(self.base_url, href)
                    file_name = link.text.strip()
                    if not file_name:
                        file_name = link.get('title', f'file_{downloaded_count+1}')
                    
                    # Очищаем имя файла
                    file_name = self._sanitize_filename(file_name)
                    file_path = os.path.join(tender_dir, file_name)
                    
                    # Скачиваем файл
                    if self._download_file(file_url, file_path):
                        downloaded_count += 1
                        
                        # Если это архив - распаковываем
                        if file_name.endswith('.zip') or file_name.endswith('.rar'):
                            self._extract_archive(file_path, tender_dir)
            
            print(f"  📁 Скачано файлов: {downloaded_count}")
            return downloaded_count
            
        except Exception as e:
            print(f"  ❌ Ошибка при скачивании: {e}")
            return 0
    
    def _download_file(self, url, file_path):
        """Скачивает один файл"""
        try:
            print(f"    ⬇️ Скачивание: {os.path.basename(file_path)}")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"    ✅ Сохранено: {os.path.basename(file_path)} ({len(response.content)} байт)")
            return True
            
        except Exception as e:
            print(f"    ❌ Ошибка скачивания: {e}")
            return False
    
    def _extract_archive(self, archive_path, extract_to):
        """Распаковывает архив"""
        try:
            if archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                print(f"    📦 Распакован ZIP архив")
        except Exception as e:
            print(f"    ⚠️ Ошибка распаковки: {e}")
    
    def _sanitize_filename(self, filename):
        """Очищает имя файла от недопустимых символов"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    
    def process_tenders(self):
        """Основной метод: обрабатывает все тендеры из Excel"""
        print("="*60)
        print("🚀 НАЧАЛО ОБРАБОТКИ ТЕНДЕРОВ")
        print("="*60)
        
        if not os.path.exists(self.excel_file):
            print(f"❌ Файл {self.excel_file} не найден!")
            return
        
        # Загружаем Excel
        wb = load_workbook(self.excel_file)
        ws = wb.active
        
        # Определяем колонки
        col_number = 1  # Номер тендера в колонке A
        
        # Проверяем наличие данных
        print(f"\n📌 Проверка данных в файле...")
        test_value = ws.cell(row=2, column=col_number).value
        print(f"   Значение в A2: {test_value}")
        
        if not test_value:
            print("❌ В колонке A нет номеров тендеров!")
            return
        
        # Очищаем и выводим первый номер для проверки
        clean_test = self.clean_tender_number(test_value)
        print(f"   Очищенный номер: {clean_test}")
        
        # Находим колонки Город и Файлы скачаны
        col_city = None
        col_downloaded = None
        
        for col in range(1, 20):
            header = ws.cell(row=1, column=col).value
            if header:
                if 'Город' in str(header):
                    col_city = col
                if 'Файлы скачаны' in str(header):
                    col_downloaded = col
        
        # Если колонок нет - добавляем
        if not col_city:
            col_city = ws.max_column + 1
            ws.cell(row=1, column=col_city, value='Город')
            print(f"📌 Добавлена колонка 'Город' ({col_city})")
        
        if not col_downloaded:
            col_downloaded = ws.max_column + 1
            ws.cell(row=1, column=col_downloaded, value='Файлы скачаны')
            print(f"📌 Добавлена колонка 'Файлы скачаны' ({col_downloaded})")
        
        wb.save(self.excel_file)
        
        # Обрабатываем каждую строку
        total_rows = ws.max_row
        print(f"\n📊 Всего строк с данными: {total_rows - 1}")
        
        processed_count = 0
        skipped_count = 0
        
        for row in range(2, total_rows + 1):
            raw_number = ws.cell(row=row, column=col_number).value
            if not raw_number:
                continue
            
            # Очищаем номер тендера
            tender_number = self.clean_tender_number(raw_number)
            if not tender_number:
                print(f"\n⚠️ Не удалось очистить номер: {raw_number}")
                continue
            
            print(f"\n{'='*50}")
            print(f"📌 Тендер {row-1}/{total_rows-1}: {tender_number}")
            print(f"{'='*50}")
            
            # Проверяем, нужно ли обрабатывать
            downloaded_status = ws.cell(row=row, column=col_downloaded).value
            if downloaded_status == 'True' or downloaded_status == True:
                print(f"  ⏭️ Уже обработан, пропускаем")
                skipped_count += 1
                continue
            
            processed_count += 1
            
            # Парсим город
            city = self.parse_city(tender_number)
            ws.cell(row=row, column=col_city, value=city)
            
            # Скачиваем файлы
            files_count = self.download_files(tender_number)
            
            # Обновляем статус
            if files_count > 0:
                ws.cell(row=row, column=col_downloaded, value='True')
                ws.cell(row=row, column=col_downloaded).fill = self.green_fill
                print(f"  ✅ Обработка завершена, скачано {files_count} файлов")
            else:
                ws.cell(row=row, column=col_downloaded, value='False')
                ws.cell(row=row, column=col_downloaded).fill = self.red_fill
                print(f"  ⚠️ Файлы не найдены")
            
            # Сохраняем после каждого тендера
            wb.save(self.excel_file)
            print(f"  💾 Прогресс сохранен")
            
            # Пауза между запросами
            time.sleep(2)
        
        print("\n" + "="*60)
        print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"📊 Обработано новых: {processed_count}")
        print(f"📊 Пропущено (уже обработаны): {skipped_count}")
        print("="*60)


def main():
    downloader = TenderFilesDownloader('tenders.xlsx')
    downloader.process_tenders()


if __name__ == "__main__":
    main()