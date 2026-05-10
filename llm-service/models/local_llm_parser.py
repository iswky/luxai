"""
Парсер на локальной LLM через Ollama.

Установка Ollama:
    # Linux / macOS
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Windows
    https://ollama.com/download

Загрузка модели:
    ollama pull qwen2.5:7b-instruct
    
Использование:
    parser = LocalLLMParser(model="qwen2.5:7b-instruct")
    result = parser.parse_pdf("tender.pdf")
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    import ollama
except ImportError:
    raise ImportError(
        "Установите ollama-python:\n"
        "pip install ollama"
    )

from pdf_extractor import PDFExtractor
import prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalLLMParser:
    """
    Парсер на локальной LLM.
    
    Рекомендуемые модели (по убыванию качества):
    - qwen2.5:7b-instruct    — лучший для русского и таблиц
    - mistral:7b-instruct    — быстрый, хорош для структурированных данных
    - llama3.1:8b-instruct   — универсальный
    - phi3:mini              — самый лёгкий (4GB RAM)
    """
    
    RECOMMENDED_MODELS = {
        "best": "qwen2.5:7b-instruct",
        "fast": "mistral:7b-instruct", 
        "light": "phi3:mini",
    }
    
    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        system_prompt: str = "Ты ИИ-ассистент. Отвечай строго в формате JSON.",
        user_prompt: str = "Извлеки данные из документа: {document}",
        temperature: float = 0.1, 
    ):
        self.model = model
        self.temperature = temperature
        self.pdf_extractor = PDFExtractor()
        
        # Передаем текст промптов напрямую
        self.set_prompt(system_prompt, user_prompt)
        
        # Проверяем доступность модели
        self._check_model()
    
    def _check_model(self) -> None:
        """Проверяет что модель скачана."""
        try:
            models = ollama.list()
            model_names = [m['name'] for m in models.get('models', [])]
            
            if not any(self.model in name for name in model_names):
                logger.warning(
                    f"Модель {self.model} не найдена.\n"
                    f"Скачайте: ollama pull {self.model}"
                )
        except Exception as e:
            logger.error(f"Не удалось проверить модели Ollama: {e}")
    
    def set_prompt(self, system_text: str, user_text: str) -> None:
        """Устанавливает текстовый промпт пользователя."""
        
        # Создаем мини-класс на лету, чтобы не ломать логику в parse_text, 
        # который ожидает self.prompt.system и self.prompt.user_template
        class CustomPrompt:
            system = system_text
            user_template = user_text
            description = "Кастомный текстовый промпт"
            
        self.prompt = CustomPrompt()
        logger.info(f"Установлен кастомный промпт. Длина system: {len(system_text)}, user: {len(user_text)}")
    
    def parse_pdf(self, pdf_path: str, extra_vars: dict = None, **kwargs):
        # 1. Получаем все блоки документа одним списком в порядке их следования
        stream = self.pdf_extractor.extract_as_stream(pdf_path)
        
        # 2. Группируем блоки: всё, что относится к Позиции 1, Позиции 2 и т.д.
        logical_item_chunks = self.pdf_extractor.group_stream_by_items(stream)
        
        print("\n" + "="*50)
        print(f"📊 ЛОГИЧЕСКИЕ ПОЗИЦИИ (найдено {len(logical_item_chunks)}):")
        for i, chunk in enumerate(logical_item_chunks, 1):
            pages = sorted(list(set([b.page for b in chunk])))
            p_range = f"{pages[0]}-{pages[-1]}" if len(pages) > 1 else f"{pages[0]}"
            print(f"  📦 Позиция {i}: блоки со страниц {p_range} ({len(chunk)} блоков)")
        print("="*50 + "\n")

        final_results = []
        for i, chunk in enumerate(logical_item_chunks, 1):
            # Собираем блоки чанка в финальный текст
            full_context = self.pdf_extractor.blocks_to_markdown(chunk)
            
            logger.info(f"🤖 Парсинг позиции {i}...")
            try:
                result = self.parse_text(full_context, extra_vars)
                if isinstance(result, list):
                    final_results.extend(result)
                else:
                    final_results.append(result)
            except Exception as e:
                logger.error(f"❌ Ошибка в позиции {i}: {e}")

        return final_results
    
    def parse_text(
        self,
        document_text: str,
        extra_vars: dict[str, str] | None = None,
    ) -> list[dict] | dict:
        """Парсит уже извлечённый текст."""
        vars_ = {"document": document_text, **(extra_vars or {})}
        user_message = self.prompt.user_template
        for key, value in vars_.items():
            user_message = user_message.replace(f"{{{key}}}", str(value))
        
        logger.info(
            f"🤖 Запуск LLM | модель={self.model} | "
            f"символов={len(document_text):,}"
        )
        
        # Вызов Ollama
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.prompt.system},
                {"role": "user", "content": user_message},
            ],
            options={
                "temperature": self.temperature,
                "num_predict": 8192,  # макс токенов ответа
                "num_ctx": 32768
            }
        )
        
        raw = response['message']['content']
        logger.info(f"✓ Ответ получен, длина: {len(raw)} символов")
        print(raw)

        return self._parse_json(raw)
    
    def _parse_chunked(
        self,
        doc: "PDFDocument",
        chunk_size: int,
        extra_vars: dict[str, str] | None,
    ) -> list[dict]:
        """
        Парсинг большого документа по частям.
        Используется для документов > 50 страниц.
        """
        logger.info(
            f"📚 Chunked parsing: {doc.total_pages} страниц → "
            f"чанки по {chunk_size}"
        )
        
        all_results = []
        num_chunks = (doc.total_pages + chunk_size - 1) // chunk_size
        
        for i in range(num_chunks):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, doc.total_pages)
            
            logger.info(f"   Чанк {i+1}/{num_chunks}: страницы {start+1}-{end}")
            
            chunk_text = doc.get_text(page_range=(start, end))
            result = self.parse_text(chunk_text, extra_vars)
            
            if isinstance(result, list):
                all_results.extend(result)
            else:
                all_results.append(result)
        
        logger.info(f"✓ Всего извлечено позиций: {len(all_results)}")
        return all_results
    
    def _parse_json(self, raw: str) -> list[dict] | dict:
        """Извлекает JSON из ответа модели."""
        clean = raw.strip()
        
        # Убираем markdown блоки
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) >= 2 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        
        try:
            result = json.loads(clean)
            if isinstance(result, list):
                logger.info(f"Распарсено позиций: {len(result)}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Raw (first 500): {raw[:500]}")
            raise
    
    def save(self, data: list[dict] | dict, path: str) -> None:
        """Сохраняет результат."""
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"💾 Сохранено: {path}")


# ──────────────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("""
Использование:
    python local_llm_parser.py <файл.pdf> [опции]
    
Опции:
    --model qwen2.5:7b-instruct    # модель Ollama
    --prompt tech_spec_v1           # промпт из реестра
    --output result.json            # сохранить результат
    --chunk-size 10                 # разбить на чанки (для длинных PDF)
    
Примеры:
    # Базовый запуск
    python local_llm_parser.py tender.pdf
    
    # С указанием модели
    python local_llm_parser.py tender.pdf --model mistral:7b-instruct
    
    # Длинный документ (разбиваем на чанки)
    python local_llm_parser.py big_tender.pdf --chunk-size 15 --output result.json
        """)
        sys.exit(1)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_file")
    parser.add_argument("--model", default="qwen2.5:7b-instruct")
    parser.add_argument("--output", "-o")
    parser.add_argument("--chunk-size", type=int)
    
    args = parser.parse_args()


    # Парсим
    llm_parser = LocalLLMParser(model=args.model, user_prompt=prompt.user_prompt, system_prompt=prompt.system_prompt)
    result = llm_parser.parse_pdf(
        args.pdf_file,
        chunk_size=args.chunk_size
    )
    
    # Выводим или сохраняем
    if args.output:
        llm_parser.save(result, args.output)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
