from typing import List, Tuple, Any
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
from openpyxl.styles import PatternFill
import os
import re


def load_keywords_from_file(filename: str = "file_filter_keywords.txt") -> List[str]:
    """
    Загружает ключевые слова из текстового файла.
    
    Формат файла: каждое ключевое слово на новой строке.
    Пустые строки и строки начинающиеся с # игнорируются.
    
    Args:
        filename: путь к файлу с ключевыми словами
        
    Returns:
        список ключевых слов
    """
    keywords = []
    
    # Проверяем существование файла
    if not os.path.exists(filename):
        print(f"⚠️ Файл {filename} не найден. Использую стандартные ключевые слова.")
        return get_default_keywords()
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                
                keywords.append(line)
        
        if not keywords:
            print(f"⚠️ Файл {filename} не содержит ключевых слов. Использую стандартные.")
            return get_default_keywords()
        
        print(f"✅ Загружено {len(keywords)} ключевых слов из {filename}")
        return keywords
        
    except Exception as e:
        print(f"❌ Ошибка при чтении {filename}: {e}")
        print("Использую стандартные ключевые слова.")
        return get_default_keywords()

def get_default_keywords() -> List[str]:
    """
    Возвращает стандартный список ключевых слов (если файл не найден).
    """
    return [
        "описание объекта закупки",
        "ООЗ",
        "наименование объекта закупки",
        "технические характеристики",
        "ТЗ",
        "техническое задание",
        "требования к товару",
        "характеристики товара",
        "функциональные характеристики",
        "показатели товара",
        "спецификация",
        "перечень поставляемого товара",
        "соответствие товара",
        "КТРУ",
        "каталог товаров работ услуг"
    ]

green_fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
keywords: List[str] = load_keywords_from_file()

# Регулярное выражение для быстрого поиска (регистронезависимое)
KEYWORDS_PATTERN = re.compile(
    r"(" + "|".join(re.escape(kw) for kw in keywords) + r")",
    re.IGNORECASE
)

def delete_files(path: str, filenames: List[str]):
    """
    Простая версия удаления файлов.
    """
    for filename in filenames:
        file_path = os.path.join(path, filename)

        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension in ['.pdf']:
            continue

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Удален: {filename}")
            else:
                print(f"Файл не найден: {filename}")
        except Exception as e:
            print(f"Ошибка при удалении {filename}: {e}")

def convert_to_pdf(path: str, files: List[str]):
    """
    Конвертирует указанные файлы в PDF формат.
    Поддерживает: .txt, .docx, .doc, .jpg, .jpeg, .png, .html
    
    Args:
        path: Путь до папки с файлами
        files: Список имен файлов для конвертации
    """
    # Проверяем существование директории
    if not os.path.exists(path):
        raise FileNotFoundError(f"Директория '{path}' не существует")
    
    if not os.path.isdir(path):
        raise NotADirectoryError(f"'{path}' не является директорией")
    
    converted_files = []
    failed_files = []
    
    for filename in files:
        file_path = os.path.join(path, filename)
        
        # Проверяем существование файла
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {filename}")
            failed_files.append(filename)
            continue
        
        # Получаем расширение файла
        file_extension = os.path.splitext(filename)[1].lower()
        output_filename = os.path.splitext(filename)[0] + ".pdf"
        output_path = os.path.join(path, output_filename)
        
        try:               
            if file_extension in ['.pdf', '.xlsx', '.xls']:
                continue
            if file_extension in ['.docx', '.doc']:
                convert_word_to_pdf(file_path, output_path)
            else:
                print(f"⚠️ Неподдерживаемый формат: {filename}")
                failed_files.append(filename)
                continue
            
            print(f"✅ Конвертирован: {filename} -> {output_filename}")
            converted_files.append(filename)
            
        except Exception as e:
            print(f"❌ Ошибка при конвертации {filename}: {str(e)}")
            failed_files.append(filename)
    
    # Вывод статистики
    print("\n" + "="*50)
    print(f"📊 Статистика конвертации:")
    print(f"   Успешно: {len(converted_files)} файлов")
    print(f"   Ошибок: {len(failed_files)} файлов")
    
    if failed_files:
        print(f"\n❌ Не удалось конвертировать: {', '.join(failed_files)}")

# Вспомогательные функции для разных форматов:
def convert_word_to_pdf(input_path: str, output_path: str):
    """Конвертирует Word документ в PDF"""
    from docx2pdf import convert

    # Конвертация одного файла
    convert(input_path)
    # или указать выходной путь
    convert("документ.docx", "результат.pdf")

def delete_extra_files(path: str, Neccesary_files: List[str]):
    """
    Удаляет все файлы в указанной директории, кроме указанных в Neccesary_files.
    
    Args:
        path: Путь до папки с файлами
        Neccesary_files: Список имен файлов, которые необходимо сохранить
    """
    # Проверяем, существует ли директория
    if not os.path.exists(path):
        raise FileNotFoundError(f"Директория '{path}' не существует")
    
    # Проверяем, является ли путь директорией
    if not os.path.isdir(path):
        raise NotADirectoryError(f"'{path}' не является директорией")
    
    # Получаем список всех файлов в директории
    all_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    
    print(all_files)

    # Создаем множество необходимых файлов для быстрого поиска
    necessary_set = set(Neccesary_files)
    
    # Удаляем лишние файлы
    deleted_count = 0
    for file in all_files:
        if file not in necessary_set:
            print(f"deleting {file}")
            file_path = os.path.join(path, file)
            try:
                os.remove(file_path)
                print(f"Удален: {file}")
                deleted_count += 1
            except Exception as e:
                print(f"Ошибка при удалении '{file}': {e}")
    
    print(f"\nУдалено файлов: {deleted_count}")
    print(f"Сохранено файлов: {len(necessary_set & set(all_files))}")

def check_keywords_in_file(file_path: str, keywords_pattern: re.Pattern = KEYWORDS_PATTERN) -> bool:
    """
    Проверяет, содержит ли файл хотя бы одно ключевое слово.
    
    Поддерживаемые форматы: .txt, .docx, .pdf, .xlsx, .odt, .ods, .rtf
    
    Args:
        file_path: путь к файлу
        keywords_pattern: скомпилированное регулярное выражение
        
    Returns:
        True если найдено хотя бы одно ключевое слово, иначе False
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        # Текстовые файлы и HTML
        if ext in ['.txt', '.html', '.htm', '.xml', '.csv', '.md', '.rst']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024 * 1024)  # читаем первые 1МБ для скорости
            return bool(keywords_pattern.search(content))
        
        # DOCX
        elif ext == '.docx':
            try:
                from docx import Document
                doc = Document(file_path)
                text = ' '.join([para.text for para in doc.paragraphs])
                # также проверяем таблицы
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            text += ' ' + cell.text
                match = keywords_pattern.search(text[:1024*1024])
                if match:
                    print(f"keyword: {match.group(0)}")
                    return True
                else:
                    return False
            except ImportError:
                print("⚠️ python-docx не установлен. Установите: pip install python-docx")
                return False
        
        # PDF
        elif ext == '.pdf':
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text = ''
                for page in reader.pages[:10]:  # первые 10 страниц
                    text += page.extract_text() or ''
                return bool(keywords_pattern.search(text[:1024*1024]))
            except ImportError:
                print("⚠️ pypdf не установлен. Установите: pip install pypdf")
                return False
        
        # Excel
        elif ext in ['.xlsx', '.xls']:
            try:
                from openpyxl import load_workbook
                
                # Загружаем workbook (только .xlsx, .xls не поддерживается openpyxl)
                wb = load_workbook(file_path, read_only=True, data_only=True)
                
                text_parts = []
                char_count = 0
                max_chars = 1024 * 1024  # 1 МБ
                
                # Проходим по всем листам
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    
                    # Проходим по всем строкам
                    for row in ws.iter_rows(values_only=True):
                        for cell in row:
                            if cell is not None:
                                cell_str = str(cell)
                                text_parts.append(cell_str)
                                char_count += len(cell_str)
                                
                                # Если набрали достаточно текста, проверяем
                                if char_count >= max_chars:
                                    combined_text = ' '.join(text_parts)
                                    match = keywords_pattern.search(combined_text)
                                    if match:
                                        print(f"keyword: {match}")
                                        wb.close()
                                        return True
                                    # Сбрасываем для продолжения
                                    text_parts = []
                                    char_count = 0
                    
                    # Проверяем текущий лист после обработки
                    if text_parts:
                        combined_text = ' '.join(text_parts)
                        match = keywords_pattern.search(combined_text)
                        if match:
                            print(f"keyword: {match}")
                            wb.close()
                            return True
                        text_parts = []
                        char_count = 0
                
                wb.close()
                return False     
            except ImportError:
                print("⚠️ openpyxl не установлен. Установите: pip install openpyxl")
                return False
            except Exception as e:
                print(f"⚠️ Ошибка чтения Excel {file_path}: {e}")
                return False
        else:
            # Неподдерживаемый формат, пропускаем
            return False
            
    except Exception as e:
        print(f"⚠️ Ошибка при чтении {file_path}: {e}")
        return False

def check_filename_for_keywords(filename: str, pattern: re.Pattern = KEYWORDS_PATTERN):
    """
    Проверяет, содержит ли название файла хотя бы одно ключевое слово.
    
    Args:
        filename: имя файла (с расширением или без)
        pattern: скомпилированное регулярное выражение
    
    Returns:
        True если найдено хотя бы одно ключевое слово, иначе False
    """
    # Убираем расширение файла для проверки
    name_without_ext = os.path.splitext(filename)[0]
    return bool(pattern.search(name_without_ext))

def find_files_with_keywords(
    path: str,
    file_list: List[str], 
    keywords_pattern: re.Pattern = KEYWORDS_PATTERN
) -> List[str]:
    """
    Находит файлы, содержащие ключевые слова.
    
    Args:
        file_list: список путей к файлам для проверки
        keywords_pattern: скомпилированное регулярное выражение
        on_no_match: функция, которая вызывается, если не найдено ни одного файла.
                     Принимает исходный список файлов, возвращает новый список.
    
    Returns:
        список файлов, в которых найдены ключевые слова
    """
    
    # Шаг 1: ищем файлы с ключевыми словами
    matched_files: List[str] = []
    
    for file_name in file_list:
        print(f"🔍 Проверяем: {os.path.basename(file_name)}")
        if (check_filename_for_keywords(file_name)):
            matched_files.append(file_name)
            print(f"   ✅ Найдены ключевые слова" )
            continue

        print(f"🔍 Проверяем внутренности файла: {os.path.basename(file_name)}")
        if (check_keywords_in_file(path + '/' + file_name)):
            matched_files.append(file_name)
            print(f"   ✅ Найдены ключевые слова")


    print(matched_files)
    
    return matched_files

def read_tenders_info(filename: str) -> List[Tuple[Any, Any, int]]:
    wb: Workbook = load_workbook(filename)
    ws: Worksheet = wb.active

    pairs: List[Tuple[Any, Any, int]] = []
    for row in range(2, ws.max_row + 1):
        if (ws.cell(row=row, column=10).value == 'True'):
            val_1: Any = ws.cell(row=row, column=1).value[2:]
            val_11: Any = ws.cell(row=row, column=11).value
            pairs.append((val_1, val_11, row))

    return pairs
        
def file_filter():
    tenders_info: List[Tuple[Any, Any, int]] = read_tenders_info("tenders.xlsx")

    wb: Workbook = load_workbook("tenders.xlsx")
    ws: Worksheet = wb.active

    i = 2
    for number, flag, row_num in tenders_info:
        if (flag != "False"):
            i += 1
            continue

        print(f"Рассматриваем файлы тендера {number}")

        folder_path: str = "./tenders_files/" + number
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            continue

        files_in_folder = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

        files_with_keywords = find_files_with_keywords(folder_path, files_in_folder)

        delete_extra_files(folder_path, files_with_keywords)

        if (not files_with_keywords):
            continue

        convert_to_pdf(folder_path, files_with_keywords)

        delete_files(folder_path, files_with_keywords)

        ws.cell(row=row_num, column=11, value='True')
        ws.cell(row=row_num, column=11).fill = green_fill

        wb.save("tenders.xlsx")

if __name__ == "__main__":
    file_filter()       