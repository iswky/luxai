from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.workbook.workbook import Workbook
from openpyxl.styles import PatternFill
from openpyxl import load_workbook
from datetime import datetime



def clear_tender(row: int):
    wb: Workbook = load_workbook("tenders.xlsx")
    ws: Worksheet = wb.active

    no_fill = PatternFill(fill_type=None)

    for i in range(1, 12):
        ws.cell(row=row, column=i).value = ""
        ws.cell(row=row, column=i).fill = no_fill
    

def tender_validator():
    wb: Workbook = load_workbook("tenders.xlsx")
    ws: Worksheet = wb.active

    for row in range(2, ws.max_row + 1):
        tender_id: str = ws.cell(row=row, column=1).value[2:]
        date_string: str = ws.cell(row=row, column=6).value

        given_date = datetime.strptime(date_string, "%d.%m.%Y").date()

        today = datetime.now().date()

        if given_date < today:
            clear_tender(row)

            # здесь должно быть удаление всех файлов тендера
            # delete *
            #     from tenders
            # where id = tender_id