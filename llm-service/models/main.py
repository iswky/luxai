import pdfplumber
import pandas as pd
from openai import OpenAI

# Настройки для Ollama
client = OpenAI(
    base_url="http://127.0.0.1:11434/v1", # Порт Ollama по умолчанию
    api_key="ollama" # Ollama игнорирует ключ, но поле не должно быть пустым
)

# Имя твоей модели из ModelFile (например, 'gemma4-pdf')
MODEL_NAME = "tender-parser" 
PDF_FILE = "123.pdf"

def extract_pdf_data(pdf_path):
    full_content = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Извлекаем таблицы в Markdown
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        df = pd.DataFrame(table)
                        if not df.empty:
                            full_content.append(f"\n[Таблица, стр {i+1}]:\n{df.to_markdown(index=False)}\n")
                
                # Извлекаем текст
                text = page.extract_text()
                if text:
                    full_content.append(f"\n[Текст, стр {i+1}]:\n{text}")
        return "\n".join(full_content)
    except Exception as e:
        print(f"Ошибка при чтении PDF: {e}")
        return None

# 1. Читаем PDF
print(f"Обработка {PDF_FILE}...")
context_text = extract_pdf_data(PDF_FILE)

user_prompt = """
КРИТИЧЕСКОЕ ПРАВИЛО: НИКОГДА не возвращай пустой массив []. Если текст непонятен, извлеки хотя бы названия оборудования и сложи сырой текст в блок "unparsed_features". Сохрани максимум данных!

=== ПРАВИЛО ИЕРАРХИИ (ВЛОЖЕННОСТЬ) ===
Если в тексте описывается "Комплекс", "Лаборатория" или "Набор" (например, "Цифровая лаборатория"), создай ОДИН корневой объект.
Все сложные устройства внутри него (датчики, микроскопы, ноутбуки) помещай в массив "components".
Мелкую комплектацию (провода, штативы, болты, карточки, софт) НЕ делай компонентами! Объединяй их в массив строк внутри блока "grouped_features".

=== ШАБЛОН JSON ===
[
  {
    "product_type": "<выбери: lab_kit | sensor | interactive_panel | projector | computing | other>",
    "product_name": "<полное наименование из текста>",
    "quantity": <число или null>,
    
    "numerical_requirements": {
      // СЮДА СТРОГО ТОЛЬКО ЧИСЛА С УСЛОВИЯМИ (gte, lte, eq)
      // Пример: "яркость_люмен": { "gte": 3000 }
    },
    
    "string_and_bool_features": {
      // СЮДА СТРОГО СТРОКИ И БУЛЕВЫ ЗНАЧЕНИЯ (без gte/lte)
      // Пример: "наличие_wifi": true, "тип_матрицы": "IPS"
    },

    "grouped_features": {
      // СЮДА МАССИВЫ СТРОК ДЛЯ ОДНОТИПНЫХ ДАННЫХ
      // Пример: "комплектация": ["кабель USB", "штатив"], "образовательные_модули": ["Химия", "Физика"]
    },

    "components": [
      // ВЛОЖЕННЫЕ УСТРОЙСТВА. У них точно такая же структура:
      // { "component_type": "...", "component_name": "...", "numerical_requirements": {...}, "string_and_bool_features": {...}, "grouped_features": {...} }
    ],
    
    "unparsed_features": ["<сюда кидай куски текста, если не знаешь, как их разбить по правилам>"]
  }
]

=== ПРАВИЛА ИЗВЛЕЧЕНИЯ И НАИМЕНОВАНИЯ КЛЮЧЕЙ ===
Ты должен подготовить данные для математического сравнения.

1. ФОРМАТ КЛЮЧЕЙ: СТРОГО snake_case. Единицы измерения ОБЯЗАТЕЛЬНО должны быть в конце ключа!
   - Правильно: "оперативная_память_гб", "диапазон_температуры_мин_с", "время_отклика_мс".
   - Неправильно: "оперативная_память", "диапазон", "отклик".

2. ПРАВИЛА ДЛЯ numerical_requirements:
   Очищай значения от текста и букв, оставляй только цифры!
   - Если "не менее X" / "от X" / ">= X"   → { "gte": X }
   - Если "не более X" / "до X" / "<= X"   → { "lte": X }
   - Если "от X до Y" / "≥X и ≤Y"          → { "gte": X, "lte": Y }
   - Если точное значение                  → { "eq": X }

3. ОСОБЫЕ ПРАВИЛА:
   - Разрешения (например, 1920x1080) разбивай на числа! → "разрешение_ширина_px": { "gte": 1920 }, "разрешение_высота_px": { "gte": 1080 }.
   - Гарантию переводи в месяцы: "гарантия_месяцев": { "gte": 36 }.

4. ПРАВИЛА ДЛЯ string_and_bool_features:
   - "наличие" / "да" / "встроено" → true.
   - "нет" / "отсутствует" → false.
   - Форматы (16:9), цвета, типы матриц (IPS) пиши чистой строкой. Запрещено использовать gte/lte для строк!

=== ПРИМЕР ===
ВХОДНОЙ ТЕКСТ: "1. Цифровая лаборатория. Кол-во 1. Датчик температуры (от -20 до +110 °С, погрешность не более 1°С). В комплекте: софт, кабель USB, кейс. Разрешение экрана не менее 1920*1080."
РЕЗУЛЬТАТ:
[
  {
    "product_type": "lab_kit",
    "product_name": "Цифровая лаборатория",
    "quantity": 1,
    "numerical_requirements": {
      "разрешение_ширина_px": { "gte": 1920 },
      "разрешение_высота_px": { "gte": 1080 }
    },
    "string_and_bool_features": {},
    "grouped_features": {
      "комплектация": ["софт", "кабель USB", "кейс"]
    },
    "components": [
      {
        "component_type": "sensor",
        "component_name": "Датчик температуры",
        "numerical_requirements": {
          "диапазон_измерений_с": { "gte": -20, "lte": 110 },
          "погрешность_с": { "lte": 1 }
        },
        "string_and_bool_features": {},
        "grouped_features": {}
      }
    ],
    "unparsed_features": []
  }
]"""

system_prompt = """Ты — строгий аналитический парсер технических спецификаций из документов российских госзакупок.
Твоя задача — извлечь требования к товарам и вернуть строго JSON-массив. Этот JSON в будущем будет использоваться кодом для АВТОМАТИЧЕСКОГО МАТЕМАТИЧЕСКОГО СРАВНЕНИЯ с предложениями поставщиков.
"""

if context_text:
    # 2. Запрос к Ollama
    print(f"Отправка запроса в модель {MODEL_NAME}...")
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
                {"role": "user", "content": f"{user_prompt}\n\n{context_text}"}
            ]
        )
        print("\nОТВЕТ:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка при запросе к Ollama: {e}")