import g4f
from g4f.client import Client
import pdfplumber
import time

def extract_clean_tables(path):
    """Достаем только таблицы в Markdown, чтобы не перегружать нейронку"""
    formatted_data = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    # Убираем None и лишние пробелы
                    clean_row = [str(c).strip().replace('\n', ' ') if c else "" for c in row]
                    formatted_data += "| " + " | ".join(clean_row) + " |\n"
    return formatted_data

# 1. Готовим данные
FILE_PATH = "123.pdf"
print("Парсим PDF...")
pdf_tables = extract_clean_tables(FILE_PATH)

# Режем до 7000 символов - это лимит, при котором провайдеры почти никогда не выдают "Busy"
pdf_tables = pdf_tables[:7000] 

# 2. Список провайдеров, которые сейчас реально работают с большими файлами
# Blackbox - №1 для файлов, DuckDuckGo - очень стабильный
working_providers = [
    g4f.Provider.DeepInfra,
    g4f.Provider.DuckDuckGo,
    g4f.Provider.Airforce,
    g4f.Provider.GigaChat
]

client = Client()

def try_ask_ai():
    for provider in working_providers:
        try:
            print(f"Пробую провайдера: {provider.__name__}...")
            response = client.chat.completions.create(
                model="", # или gpt-4
                provider=provider,
                messages=[
                    {"role": "user", "content": f"Вот таблица из PDF. Проанализируй её и сохрани структуру:\n\n{pdf_tables}"}
                ]
            )
            content = response.choices[0].message.content
            if content:
                return content
        except Exception as e:
            print(f"Провайдер {provider.__name__} выдал ошибку или Busy. Пробую следующего...")
            time.sleep(1) # Небольшая пауза
    return None

# 3. Запуск
print("Начинаю общение с нейросетями...")
result = try_ask_ai()

if result:
    print("\n=== ПОЛУЧЕННЫЙ ОТВЕТ ===\n")
    print(result)
else:
    print("\n[!] Все провайдеры сейчас перегружены или не смогли обработать такой объем данных.")
    print("Попробуй обрезать PDF или подождать 5 минут.")