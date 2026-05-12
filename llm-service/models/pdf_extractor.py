import re
import pdfplumber
import logging
from dataclasses import dataclass
from typing import List, Any

logger = logging.getLogger(__name__)

@dataclass
class ContentBlock:
    type: str  # Теперь тут всегда будет только "table"
    content: Any
    page: int

class PDFExtractor:
    def extract_as_stream(self, pdf_path: str) -> List[ContentBlock]:
        """Извлекает данные как поток блоков (СТРОГО ТОЛЬКО ТАБЛИЦЫ)."""
        stream = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                tables = page.find_tables()
                
                # Игнорируем весь текст на странице, парсим только таблицы
                for table_obj in tables:
                    raw_table = table_obj.extract()
                    # Чистим от None и лишних пробелов сразу
                    cleaned = [[str(c).strip() if c else "" for c in row] for row in raw_table]
                    stream.append(ContentBlock(type="table", content=cleaned, page=i))
        return stream

    def _is_ignored_table(self, table_rows: List[List[str]]) -> bool:
        """
        Проверяет, является ли таблица вводной/сводной (ОКПД2, Запреты, КТРУ).
        """
        if not table_rows: 
            return True
            
        # Берем первые 5 строк для анализа шапки таблицы, чистим от переносов строк
        header_text = " ".join([" ".join(str(c).lower().replace('\n', ' ') for c in row) for row in table_rows[:5]])
        
        # Строгие маркеры таблицы спецификаций
        good_keywords = ["характеристик", "показател", "описание", "комплектация", "значени", "наименование товара", "параметр"]
        has_good_keywords = any(kw in header_text for kw in good_keywords)
        
        # Маркеры сводной таблицы (ОКПД2)
        bad_keywords = ["окпд", "ктру", "национальный режим", "запрет", "нмцк", "начальная цена", "ограничение"]
        
        # Если есть стоп-слова и нет явных признаков спецификации - в мусор
        if any(kw in header_text for kw in bad_keywords) and not has_good_keywords:
            return True
            
        # Если "таблица" состоит всего из 1 колонки (это просто параграф текста, ошибочно ставший таблицей)
        max_cols = max(len(row) for row in table_rows)
        if max_cols < 2:
            return True
            
        return False

    def group_stream_by_items(self, stream: List[ContentBlock]) -> List[List[ContentBlock]]:
        """
        Группирует блоки, разрезая таблицы по номерам позиций в первой колонке.
        """
        chunks = []
        current_chunk = []
        
        # СТРОГАЯ регулярка: в ячейке должна быть ТОЛЬКО цифра (и возможная точка/знак №).
        item_pattern = re.compile(r'^\s*(?:№\s*)?(\d+)\.?\s*$')
        current_item_id = 0
        tz_ended = False
        
        # Маркеры, после которых ТЗ гарантированно заканчивается и начинается контракт
        contract_markers = [
            "место поставки", "место доставки", "срок поставки", "сроки поставки", 
            "требования к качеству", "требования к упаковке", "требования к безопасности", 
            "требования к выполнению", "порядок выполнения", "гарантийные обязательства",
            "условия доставки", "порядок оплаты", "сдача-приемка"
        ]
        
        for block in stream:
            if tz_ended:
                break
                
            if block.type == "table":
                table_rows = block.content
                
                # --- УМНАЯ ФИЛЬТРАЦИЯ ---
                if self._is_ignored_table(table_rows):
                    logger.info(f"⏭️ Пропущена таблица на стр. {block.page} (сводная таблица ОКПД2)")
                    continue

                last_split_idx = 0
                table_header = []
                
                for idx, row in enumerate(table_rows):
                    if not row or not row[0]:
                        continue
                        
                    # ПРОАКТИВНАЯ ЗАЩИТА: Проверяем, не начались ли условия контракта
                    if current_item_id > 0:
                        # Берем первые две колонки и чистим их от нумерации (например "2. место поставки" -> "место поставки")
                        text = " ".join(str(c).lower() for c in row[:2])
                        text_clean = re.sub(r'^\s*(?:№\s*)?(?:\d+\.)*\d+\.?\s*', '', text).strip()
                        
                        if any(text_clean.startswith(m) for m in contract_markers):
                            logger.info(f"🛑 Обнаружен пункт договора ('{text_clean[:20]}...'). ТЗ завершено.")
                            tz_ended = True
                            # Отрезаем и сохраняем всё полезное до этого пункта
                            if idx > last_split_idx:
                                old_part = table_rows[last_split_idx:idx]
                                current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                            break
                        
                    val = str(row[0]).strip()
                    match = item_pattern.match(val)
                    
                    if match:
                        num = int(match.group(1))
                        
                        # Защита: номер должен расти, а в строке таблицы должно быть хотя бы 2 колонки
                        if num > current_item_id and len(row) > 1:
                            # 1. Отрезаем старый кусок
                            if idx > last_split_idx:
                                old_part = table_rows[last_split_idx:idx]
                                
                                if current_item_id == 0:
                                    current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                                    table_header = old_part 
                                else:
                                    current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                            
                            # 2. Закрываем чанк
                            if current_item_id > 0:
                                chunks.append(current_chunk)
                                current_chunk = []
                                # Возвращаем шапку для следующего отрезанного куска
                                if table_header:
                                    current_chunk.append(ContentBlock(type="table", content=table_header, page=block.page))
                                    
                            last_split_idx = idx
                            current_item_id = num
                
                # Если парсинг был прерван условиями контракта, выходим из обработки таблицы
                if tz_ended:
                    break
                
                # Добавляем оставшуюся часть (хвост)
                remaining_part = table_rows[last_split_idx:]
                if remaining_part:
                    current_chunk.append(ContentBlock(type="table", content=remaining_part, page=block.page))
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def blocks_to_markdown(self, blocks: List[ContentBlock]) -> str:
        md = []
        for b in blocks:
            if b.type == "table":
                md.append(f"\n[Таблица, стр {b.page}]:\n{self._table_to_markdown(b.content)}")
        return "\n".join(md)

    def _table_to_markdown(self, table: List[List[str]]) -> str:
        if not table: return ""
        processed_table = []
        for row in table:
            # Склеиваем пустые ячейки (если строка перенеслась)
            if not row[0] and processed_table:
                for i in range(len(row)):
                    if row[i]: processed_table[-1][i] += " " + row[i]
            else:
                processed_table.append(row)
        
        if not processed_table: return ""
        
        res = ["| " + " | ".join(processed_table[0]) + " |", "| " + " | ".join(["---"] * len(processed_table[0])) + " |"]
        for row in processed_table[1:]:
            res.append("| " + " | ".join(row) + " |")
        return "\n".join(res)