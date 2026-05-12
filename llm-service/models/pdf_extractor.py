import pdfplumber
import logging
from dataclasses import dataclass
from typing import List, Any

logger = logging.getLogger(__name__)

@dataclass
class ContentBlock:
    type: str  # "text" или "table"
    content: Any
    page: int

class PDFExtractor:
    def extract_as_stream(self, pdf_path: str) -> List[ContentBlock]:
        """Извлекает данные как поток блоков."""
        stream = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                # В тендерах лучше извлекать таблицы по одной
                tables = page.find_tables()
                
                # Текст страницы
                text = page.extract_text()
                if text and text.strip():
                    stream.append(ContentBlock(type="text", content=text, page=i))
                
                for table_obj in tables:
                    raw_table = table_obj.extract()
                    # Чистим от None и лишних пробелов сразу
                    cleaned = [[str(c).strip() if c else "" for c in row] for row in raw_table]
                    stream.append(ContentBlock(type="table", content=cleaned, page=i))
        return stream

    def group_stream_by_items(self, stream: List[ContentBlock]) -> List[List[ContentBlock]]:
        """
        Группирует блоки, РАЗРЕЗАЯ таблицы, если внутри них начинается новый Лот.
        """
        chunks = []
        current_chunk = []
        current_item_id = 1 # Мы сейчас ищем данные для Лота 1, ждем появления "2"

        for block in stream:
            if block.type == "table":
                table_rows = block.content
                last_split_idx = 0
                
                for idx, row in enumerate(table_rows):
                    val = row[0].replace('.', '').strip()
                    
                    # Проверяем, не началась ли новая позиция (например, "2")
                    if val.isdigit() and int(val) == current_item_id + 1:
                        # 1. Отрезаем кусок таблицы, который относится к старому лоту
                        if idx > last_split_idx:
                            old_part = table_rows[last_split_idx:idx]
                            current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                        
                        # 2. Закрываем текущий чанк (Лот 1 закончен)
                        chunks.append(current_chunk)
                        
                        # 3. Начинаем новый чанк (для Лота 2)
                        current_chunk = []
                        last_split_idx = idx
                        current_item_id += 1
                
                # Добавляем оставшуюся часть таблицы (или всю, если сплита не было)
                remaining_part = table_rows[last_split_idx:]
                if remaining_part:
                    current_chunk.append(ContentBlock(type="table", content=remaining_part, page=block.page))
            
            else:
                # Текстовый блок просто добавляем
                # (Можно добавить аналогичный сплит текста через .split("\n2."), но в тендерах 
                # позиции обычно начинаются с таблиц)
                current_chunk.append(block)
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def blocks_to_markdown(self, blocks: List[ContentBlock]) -> str:
        md = []
        for b in blocks:
            if b.type == "text":
                md.append(f"\n[Текст, стр {b.page}]:\n{b.content}")
            else:
                md.append(f"\n[Таблица, стр {b.page}]:\n{self._table_to_markdown(b.content)}")
        return "\n".join(md)

    def _table_to_markdown(self, table: List[List[str]]) -> str:
        if not table: return ""
        # Склеиваем пустые ячейки для компактности перед отправкой в LLM
        processed_table = []
        for row in table:
            if not row[0] and processed_table:
                for i in range(len(row)):
                    if row[i]: processed_table[-1][i] += " " + row[i]
            else:
                processed_table.append(row)
        
        res = ["| " + " | ".join(processed_table[0]) + " |", "| " + " | ".join(["---"] * len(processed_table[0])) + " |"]
        for row in processed_table[1:]:
            res.append("| " + " | ".join(row) + " |")
        return "\n".join(res)