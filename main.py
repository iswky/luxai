import g4f
from g4f.client import Client
import pdfplumber
import time

# we only get tables in markdown so as not to overload the neuron
def extract_clean_tables(path):
    formatted_data = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    # removing none and extra spaces
                    clean_row = [str(c).strip().replace('\n', ' ') if c else "" for c in row]
                    formatted_data += "| " + " | ".join(clean_row) + " |\n"
    return formatted_data

# 1. prepare the data
FILE_PATH = "123.pdf"
print("Парсим PDF...")
pdf_tables = extract_clean_tables(FILE_PATH)

# we cut it to 7000 characters - this is the limit at which providers almost never issue “busy”
pdf_tables = pdf_tables[:7000] 

# 2. list of providers that currently actually work with large files
# blackbox - #1 for files, duckduckgo - very stable
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
                model="", # or gpt-4
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
            time.sleep(1) # a short pause
    return None

# 3. launch
print("Начинаю общение с нейросетями...")
result = try_ask_ai()

if result:
    print("\n=== ПОЛУЧЕННЫЙ ОТВЕТ ===\n")
    print(result)
else:
    print("\n[!] Все провайдеры сейчас перегружены или не смогли обработать такой объем данных.")
    print("Попробуй обрезать PDF или подождать 5 минут.")