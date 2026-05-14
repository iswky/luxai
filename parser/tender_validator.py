from datetime import datetime
from typing import Dict, List
import shutil
import os

try:
    from db import delete_tender_from_db, get_all_from_processing_queue, remove_from_processing_queue
except ImportError:
    # if psycopg2 is not installed or we do not run it from the parser/ folder
    def delete_tender_from_db(tender_number: str) -> bool:
        print(f"db.py unavailable, tender {tender_number} untouched in DB")
        return False

    def get_all_from_processing_queue() -> list:
        return []

    def remove_from_processing_queue(tender_number: str):
        pass


TENDERS_FILES_DIR = "./tenders_files"


# column 1 stores the number with a 2-character prefix (see file_filter.py: ws.cell(...).value[2:]).the tender folder is named without these 2 characters.
def _tender_number_to_folder(tender_number: str) -> str:
    return tender_number[2:] if len(tender_number) > 2 else tender_number


# nukes the folder with tender files (if any).
def _wipe_tender_files(tender_number: str) -> None:
    folder = os.path.join(TENDERS_FILES_DIR, _tender_number_to_folder(tender_number))
    if os.path.isdir(folder):
        try:
            shutil.rmtree(folder)
            print(f"Deleted files folder: {folder}")
        except Exception as e:
            print(f"Failed to delete folder {folder}: {e}")

def deduplicate_tenders_in_excel() -> int:
    return 0

def tender_validator():
    tenders = get_all_from_processing_queue()

    for tender in tenders:
        full_number = tender['tender_number']
        date_string = tender['end_date']

        if date_string == "Не указана" or not date_string:
            continue

        try:
            given_date = datetime.strptime(str(date_string), "%d.%m.%Y").date()
        except ValueError:
            continue

        today = datetime.now().date()

        if given_date < today:
            _wipe_tender_files(full_number)
            delete_tender_from_db(full_number)
            remove_from_processing_queue(full_number)
            print(f"Tender {full_number} expired ({date_string}), cleared")