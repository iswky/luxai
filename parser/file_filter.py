from typing import List, Tuple, Any
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
from openpyxl.styles import PatternFill
from llm import parse_pdf_to_json
from db import save_tender_to_db
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

def convert_files_to_pdf(folder_path: str, files: List[str]):
    # Проверяем существование директории
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Директория '{folder_path}' не существует")
    
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"'{folder_path}' не является директорией")

    for filename in files:
        file_path = folder_path + '/' + filename

        convert1file2pdf(file_path)

def convert1file2pdf(file_path: str):
    # Проверяем существование директории
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Директория '{file_path}' не существует")

    file_extension = os.path.splitext(file_path)[1].lower()
    output_filename = os.path.splitext(file_path)[0] + ".pdf"
    
    try:               
        if file_extension in ['.pdf', '.xlsx', '.xls']:
            convert_excel_to_pdf(file_path, output_filename)
        if file_extension in ['.docx', '.doc']:
            convert_word_to_pdf(file_path, output_filename)
        else:
            print(f"⚠️ Неподдерживаемый формат: {file_path}")
        
        print(f"✅ Конвертирован: {file_path} -> {output_filename}")
        
    except Exception as e:
        print(f"❌ Ошибка при конвертации {file_path}: {str(e)}")
    


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
        # print(file_path)
        
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
            if file_extension in ['.pdf']:
                continue
            if file_extension in ['.xlsx', '.xls']:
                convert_excel_to_pdf(file_path, output_path)
            if file_extension in ['.docx']:
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
def convert_word_to_pdf(input_path: str, output_path: str = None):
    """
    Конвертирует Word документ в PDF
    
    Args:
        input_path: путь к исходному .docx файлу
        output_path: путь для сохранения .pdf файла (опционально)
    """

    import subprocess

    # Если output_path не указан, создаем рядом с исходным файлом
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + '.pdf'
    
    # Получаем директорию для output
    output_dir = os.path.dirname(output_path)
    if not output_dir:
        output_dir = '.'
    
    # Конвертация через LibreOffice
    cmd = [
        'libreoffice',
        '--headless',           # Без графического интерфейса
        '--convert-to', 'pdf',  # Конвертация в PDF
        '--outdir', output_dir, # Выходная директория
        input_path              # Входной файл
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # LibreOffice сохраняет файл с тем же именем в output_dir
        generated_pdf = os.path.join(output_dir, os.path.basename(input_path).replace('.docx', '.pdf'))
        
        # Если нужно переименовать или переместить
        if generated_pdf != output_path:
            os.rename(generated_pdf, output_path)
        
        print(f"✅ Конвертация успешна: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка конвертации: {e}")
        print(f"Stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        raise Exception("LibreOffice не установлен. Установите: sudo apt install libreoffice")

def convert_excel_to_pdf(input_path: str, output_path: str):
    """
    Конвертирует Excel в PDF с правильным чтением данных
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    # print(input_path)
    
    # Читаем с дополнительными параметрами
    df = pd.read_excel(
        input_path,
        header=None,  # Не использовать первую строку как заголовок
        keep_default_na=False,  # Не заменять пустые значения на NaN
        na_filter=False  # Отключить фильтрацию NA
    )
    
    # Удаляем полностью пустые строки и столбцы
    df = df.dropna(how='all', axis=0)  # Убираем пустые строки
    df = df.dropna(how='all', axis=1)  # Убираем пустые столбцы
    
    print(f"Размер таблицы: {df.shape}")
    
    if df.empty or df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError("Excel файл не содержит данных")
    
    # Заменяем NaN на пустые строки
    df = df.fillna('')
    
    # Вычисляем размер
    num_rows, num_cols = df.shape
    fig_width = max(12, num_cols * 2)
    fig_height = max(8, num_rows * 0.6)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('tight')
    ax.axis('off')
    
    # Создаем таблицу БЕЗ заголовков (так как header=None)
    table = ax.table(
        cellText=df.values,
        cellLoc='left',  # Выравнивание по левому краю
        loc='center',
        colWidths=[1.0/num_cols] * num_cols
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    with PdfPages(output_path) as pdf:
        pdf.savefig(fig, bbox_inches='tight', dpi=150)
    
    plt.close()
    print(f"✅ PDF сохранен: {output_path}")

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
        
def import_pdf_files_from_folder_to_database(folder_path: str, tender_number: str = None):
    """
    Парсит все PDF-файлы из папки тендера и сохраняет их в БД.

    Если в папке несколько PDF — все их позиции попадут в один тендер
    (по UPSERT в save_tender_to_db). При повторном запуске старые позиции
    тендера сносятся и записываются заново (см. db.save_tender_to_db).

    Args:
        folder_path: путь до папки с pdf-файлами тендера
        tender_number: номер тендера (если не передан — берём имя папки)
    """
    if not os.path.exists(folder_path):
        print(f"Папки {folder_path} не найдено")
        return

    if tender_number is None:
        tender_number = os.path.basename(os.path.normpath(folder_path))

    files_in_folder = [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]

    # Накапливаем items со всех pdf этого тендера, чтобы записать одним UPSERT'ом
    all_items: List[dict] = []
    processed_pdfs: List[str] = []

    for file in files_in_folder:
        file_extension = os.path.splitext(file)[1].lower()
        if file_extension != '.pdf':
            continue

        pdf_path = os.path.join(folder_path, file)
        print(f"🤖 Парсим pdf: {pdf_path}")

        try:
            parsed = parse_pdf_to_json(pdf_path)
            items = parsed.get("items", []) or []
            # Помечаем, из какого файла пришла каждая позиция
            for item in items:
                item.setdefault("_source_pdf", file)
            all_items.extend(items)
            processed_pdfs.append(file)
        except Exception as e:
            print(f"❌ Не удалось распарсить {pdf_path}: {e}")

    if not all_items:
        print(f"⚠️ В папке {folder_path} нет распарсенных позиций, в БД ничего не пишу")
        return

    merged = {"items": all_items}
    pdf_source = ", ".join(processed_pdfs) if processed_pdfs else None

    db_id = save_tender_to_db(
        tender_number=tender_number,
        parsed_json=merged,
        pdf_source_file=pdf_source,
    )

    if db_id is not None:
        print(f"💾 Тендер {tender_number} → r_luxai.tenders.id={db_id}, позиций: {len(all_items)}")
    else:
        print(f"❌ Сохранение тендера {tender_number} в БД не удалось")



def file_filter():
    tenders_info: List[Tuple[Any, Any, int]] = read_tenders_info("tenders.xlsx")

    wb: Workbook = load_workbook("tenders.xlsx")
    ws: Worksheet = wb.active

    for number, flag, row_num in tenders_info:
        if (flag != "False"):
            continue

        print(f"Рассматриваем файлы тендера {number}")

        folder_path: str = os.path.join("./tenders_files", number)
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            continue

        files_in_folder = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

        files_with_keywords = find_files_with_keywords(folder_path, files_in_folder)


        if (not files_with_keywords):   # елси мы не нашли ни один файл с нужными нам словами, то конвертируем все файлы
            convert_files_to_pdf(folder_path, files_in_folder)
        else:   # если нашли файлы с нужными словами, то конвертируем их и удаляем все остальные
            convert_files_to_pdf(folder_path, files_with_keywords)

        delete_files(folder_path, files_in_folder)

        # tender_number в Excel хранится с 2-символьным префиксом (см. read_tenders_info: value[2:]),
        # а folder_path / number — уже без префикса. В БД сохраняем полный номер из Excel,
        # для этого восстановим его из ws.
        full_tender_number = ws.cell(row=row_num, column=1).value
        import_pdf_files_from_folder_to_database(folder_path, tender_number=str(full_tender_number))

        ws.cell(row=row_num, column=11, value='True')
        ws.cell(row=row_num, column=11).fill = green_fill

        wb.save("tenders.xlsx")

if __name__ == "__main__":
    # При прямом запуске можно сразу запустить дедуп + полную обработку
    from tender_validator import deduplicate_tenders_in_excel
    from db import deduplicate_tenders_in_db

    deduplicate_tenders_in_excel()
    deduplicate_tenders_in_db()
    file_filter()