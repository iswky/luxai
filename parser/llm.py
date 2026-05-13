# llm.py -------------------- pulls technical specifications from government procurement pdfs and spits out structured json via the deepseek api.installing dependencies: pip install pdfplumber pandas tabulate openai usage: from llm import parse_pdf_to_json result = parse_pdf_to_json("tender.pdf") # result - parsed json

import json
import os
import re
import logging
import sys

from openai import OpenAI
from pdf_extractor import PDFExtractor

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ─────────────────────────── prompt───────────────────────────
SYSTEM_PROMPT = """Ты — строгий аналитический парсер технических спецификаций из документов российских госзакупок.
Твоя задача — извлечь требования к товарам и вернуть строго JSON-массив. Этот JSON в будущем будет использоваться кодом для АВТОМАТИЧЕСКОГО МАТЕМАТИЧЕСКОГО СРАВНЕНИЯ с предложениями поставщиков.

КРИТИЧЕСКОЕ ПРАВИЛО: НИКОГДА не возвращай пустой массив []. Если текст непонятен, извлеки хотя бы названия оборудования и сложи сырой текст в блок "unparsed_features". Сохрани максимум полезных данных!

=== ПРАВИЛО ФИЛЬТРАЦИИ (УДАЛЕНИЕ "МУСОРА") ===
Твоя главная цель — выделить параметры для строгого технического сравнения. Ты ДОЛЖЕН ИГНОРИРОВАТЬ и полностью исключать из JSON базовые, очевидные и малозначимые элементы комплектации, не имеющие уникальных измеримых характеристик.
Что необходимо отбрасывать:
1. Общеупотребительные детали наборов (особенно для робототехники): базовые пластиковые/металлические балки, оси, шестеренки, штифты, рамки, если к ним не предъявляются строгие числовые требования.
2. Базовую физическую мелочевку: болты, гайки, крепежи, стандартные соединительные провода и стяжки.
3. Тару и упаковку: пластиковые контейнеры для хранения, ложементы, кейсы (если кейс не является сложным устройством с зарядкой/охлаждением).

=== ПРАВИЛО ИЕРАРХИИ (ВЛОЖЕННОСТЬ) ===
Если в тексте описывается "Комплекс", "Лаборатория" или "Набор" (например, "Цифровая лаборатория"), создай ОДИН корневой объект.
Все сложные устройства внутри него (датчики, микроскопы, ноутбуки, программируемые контроллеры, моторы) помещай в массив "components".
Важную, но мелкую комплектацию, которую нельзя отбросить по правилу фильтрации (например, наличие специфического софта, образовательных модулей, методичек), НЕ делай компонентами! Объединяй их в массив строк внутри блока "grouped_features".

=== ШАБЛОН JSON ===
{
  "items": [
    {
      "product_type": "<выбери: lab_kit | robotics_kit | sensor | interactive_panel | projector | computing | other>",
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
        // СЮДА МАССИВЫ СТРОК ДЛЯ ОДНОТИПНЫХ ВАЖНЫХ ДАННЫХ
        // Пример: "образовательные_модули": ["Химия", "Физика"]
      },

      "components": [
        // ВЛОЖЕННЫЕ УСТРОЙСТВА. У них точно такая же структура:
        // { "component_type": "...", "component_name": "...", "numerical_requirements": {...}, "string_and_bool_features": {...}, "grouped_features": {...} }
      ],
      
      "unparsed_features": ["<сюда кидай куски текста, если не знаешь, как их разбить по правилам>"]
    }
  ]
}

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
ВХОДНОЙ ТЕКСТ: "1. Набор по робототехнике. Кол-во 1. Включает: программируемый контроллер (память не менее 512 Мб), 40 базовых пластиковых балок, 20 шестеренок, соединительные провода, болты, пластиковый контейнер для хранения. В комплекте программное обеспечение для программирования. Гарантия 12 месяцев."
РЕЗУЛЬТАТ:
{
  "items": [
    {
      "product_type": "robotics_kit",
      "product_name": "Набор по робототехнике",
      "quantity": 1,
      "numerical_requirements": {
        "гарантия_месяцев": { "gte": 12 }
      },
      "string_and_bool_features": {},
      "grouped_features": {
        "программное_обеспечение": ["ПО для программирования"]
      },
      "components": [
        {
          "component_type": "computing",
          "component_name": "Программируемый контроллер",
          "numerical_requirements": {
            "оперативная_память_мб": { "gte": 512 }
          },
          "string_and_bool_features": {},
          "grouped_features": {}
        }
      ],
      "unparsed_features": []
    }
  ]
}

ВЕРНИ ТОЛЬКО JSON БЕЗ КАКИХ-ЛИБО ПОЯСНЕНИЙ И МАРКДАУН-БЛОКОВ."""

# call deepseek api───────────────────
# sends the extracted text to deepseek and spits out a raw response.
def _call_deepseek(content: str, api_key: str) -> str:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        max_retries=3,
        timeout=180
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        temperature=0,          # deterministic output - important for parsing
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Вот часть PDF-документа госзакупки. "
                    "Извлеки технические требования к товарам из этого блока.\n\n"
                    f"{content}"
                ),
            },
        ],
    )

    return response.choices[0].message.content


# ─────────────────────── answer cleaning───────────────────────
# removes possible markdown wrappers and chews through json.we use \x60 (hex for `) to avoid breaking file parsing in the ide/interface.
def _clean_and_parse_json(raw: str) -> dict:
    cleaned = re.sub(r"^\x60\x60\x60(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\x60\x60\x60$", "", cleaned.strip())

    try:
        data = json.loads(cleaned)
        # we guarantee that a dict with the key items will be returned
        if isinstance(data, list):
            return {"items": data}
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return {"items": [], "unparsed_features": ["Ошибка декодирования JSON ответа"]}


# ─────────────────────── public func────────────────────
# chews through pdf with technical requirements of government procurement and spits out json.
def parse_pdf_to_json(
    pdf_path: str,
    output_json_path: str | None = None,
    api_key: str | None = None,
) -> dict:
    # 1. determine the api key
    resolved_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not resolved_key:
        raise ValueError(
            "API-ключ не найден. Передайте его параметром api_key=... "
            "или установите переменную окружения DEEPSEEK_API_KEY."
        )

    # 2. extract blocks and break them into logical positions
    logger.info(f"📄 Читаем PDF: {pdf_path}")
    extractor = PDFExtractor()
    stream = extractor.extract_as_stream(pdf_path)
    logical_chunks = extractor.group_stream_by_items(stream)

    print("\n" + "="*50)
    print(f"LOGICAL POSITIONS (found {len(logical_chunks)}):")
    for i, chunk in enumerate(logical_chunks, 1):
        pages = sorted(list(set([b.page for b in chunk])))
        p_range = f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else f"{pages[0]}"
        print(f"Position {i}: blocks from pages {p_range} ({len(chunk)} blocks)")
    print("="*50 + "\n")

    all_items = []

    # 3. we process each block separately
    for i, chunk in enumerate(logical_chunks, 1):
        context = extractor.blocks_to_markdown(chunk)
        
        if not context.strip():
            continue

        logger.info(f"🤖 Парсинг позиции {i} (символов: {len(context)})...")
        
        try:
            raw_response = _call_deepseek(context, resolved_key)
            result = _clean_and_parse_json(raw_response)
            
            items = result.get("items", [])
            all_items.extend(items)
            logger.info(f"✓ Позиция {i} обработана (извлечено объектов: {len(items)})")
        except Exception as e:
            logger.error(f"❌ Ошибка в позиции {i}: {e}")

    final_result = {"items": all_items}
    logger.info(f"✅ Анализ завершен! Всего извлечено {len(all_items)} позиций.")

    # 4. save to file
    if output_json_path is None:
        base = os.path.splitext(pdf_path)[0]
        output_json_path = base + ".json"

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(final_result, f, ensure_ascii=False, indent=2)

    logger.info(f"💾 JSON сохранён: {output_json_path}")
    return final_result


# cli──────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python llm.py <path_to.pdf> [path_to.json]")
        sys.exit(1)

    pdf = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None

    parse_pdf_to_json(pdf, output_json_path=out)