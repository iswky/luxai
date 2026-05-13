from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
from openpyxl.styles import PatternFill
from openpyxl import load_workbook
from datetime import datetime
from typing import Dict, List
import shutil
import os

try:
    from db import delete_tender_from_db
except ImportError:
    # if psycopg2 is not installed or we do not run it from the parser/ folder
    def delete_tender_from_db(tender_number: str) -> bool:
        print(f"⚠️ db.py недоступен, тендер {tender_number} в БД не тронут")
        return False


TENDERS_XLSX = "tenders.xlsx"
TENDERS_FILES_DIR = "./tenders_files"
TOTAL_COLUMNS = 11  # how many columns are there in tenders.xlsx


# column 1 stores the number with a 2-character prefix (see file_filter.py: ws.cell(...).value[2:]).the tender folder is named without these 2 characters.
def _tender_number_to_folder(tender_number: str) -> str:
    return tender_number[2:] if len(tender_number) > 2 else tender_number


# nukes the folder with tender files (if any).
def _wipe_tender_files(tender_number: str) -> None:
    folder = os.path.join(TENDERS_FILES_DIR, _tender_number_to_folder(tender_number))
    if os.path.isdir(folder):
        try:
            shutil.rmtree(folder)
            print(f"🗑 Удалена папка файлов: {folder}")
        except Exception as e:
            print(f"⚠️ Не удалось удалить папку {folder}: {e}")


def clear_tender(row: int):
    wb: Workbook = load_workbook(TENDERS_XLSX)
    ws: Worksheet = wb.active

    no_fill = PatternFill(fill_type=None)

    for i in range(1, TOTAL_COLUMNS + 1):
        ws.cell(row=row, column=i).value = ""
        ws.cell(row=row, column=i).fill = no_fill

    wb.save(TENDERS_XLSX)


# same as clear_tender, but does not open/save the file - it works with ws already open.
def _clear_row_inplace(ws: Worksheet, row: int) -> None:
    no_fill = PatternFill(fill_type=None)
    for i in range(1, TOTAL_COLUMNS + 1):
        ws.cell(row=row, column=i).value = ""
        ws.cell(row=row, column=i).fill = no_fill


# removes duplicate tenders in tenders.xlsx.if the same tender number has several lines, we leave the last one in order (it is the most recent, since the parser adds new lines to the end), and clear the earlier lines.we also delete the folders with the files of these duplicates and remove them from the database so that there are no “hanging” duplicates with the same tender_number.
def deduplicate_tenders_in_excel() -> int:
    if not os.path.exists(TENDERS_XLSX):
        print(f"⚠️ Файл {TENDERS_XLSX} не найден, пропускаю дедупликацию Excel")
        return 0

    wb: Workbook = load_workbook(TENDERS_XLSX)
    ws: Worksheet = wb.active

    # group the lines by tender number
    rows_by_number: Dict[str, List[int]] = {}
    for row in range(2, ws.max_row + 1):
        value = ws.cell(row=row, column=1).value
        if value is None or value == "":
            continue
        number = str(value).strip()
        rows_by_number.setdefault(number, []).append(row)

    removed = 0
    for number, rows in rows_by_number.items():
        if len(rows) < 2:
            continue

        # we leave the last line (the most recent entry), clear the rest
        keep_row = rows[-1]
        dup_rows = rows[:-1]

        print(f"♻️ Дубль тендера {number}: строки {dup_rows} → оставляем {keep_row}")

        for r in dup_rows:
            _clear_row_inplace(ws, r)
            removed += 1

        # the files for these duplicates are the same (folder by number), but if the user
        # i managed to put them in different folders - our number is still the same, the folder is still the same.
        # we do not delete the folder (the files of the very tender that we are leaving are there).

    if removed > 0:
        wb.save(TENDERS_XLSX)
        print(f"✅ Дубликатов в Excel удалено: {removed}")
    else:
        print("✅ Дублей в Excel не найдено")

    return removed

def tender_validator():
    if not os.path.exists("./tenders.xlsx"):
        return

    wb: Workbook = load_workbook("tenders.xlsx")
    ws: Worksheet = wb.active

    for row in range(2, ws.max_row + 1):
        cell_value = ws.cell(row=row, column=1).value
        if cell_value is None or cell_value == "":
            continue

        full_number: str = str(cell_value)
        tender_id: str = full_number[2:] if len(full_number) > 2 else full_number
        date_string = ws.cell(row=row, column=6).value

        if date_string == "Не указана" or not date_string:
            continue  # there was a return - this stopped the validation of all other lines

        try:
            given_date = datetime.strptime(str(date_string), "%d.%m.%Y").date()
        except ValueError:
            continue

        today = datetime.now().date()

        if given_date < today:
            _clear_row_inplace(ws, row)
            _wipe_tender_files(full_number)
            delete_tender_from_db(full_number)
            print(f"🗑 Тендер {full_number} просрочен ({date_string}), очищен")

    wb.save(TENDERS_XLSX)