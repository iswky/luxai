import re
import pdfplumber
import logging
from dataclasses import dataclass
from typing import List, Any

logger = logging.getLogger(__name__)

@dataclass
class ContentBlock:
    type: str  # now there will always be only "table"
    content: Any
    page: int

class PDFExtractor:
    # retrieves data as a stream of blocks (strictly tables only).
    def extract_as_stream(self, pdf_path: str) -> List[ContentBlock]:
        stream = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                tables = page.find_tables()
                
                # we ignore all the text on the page, parse only the tables
                for table_obj in tables:
                    raw_table = table_obj.extract()
                    # clear none and extra spaces immediately
                    cleaned = [[str(c).strip() if c else "" for c in row] for row in raw_table]
                    stream.append(ContentBlock(type="table", content=cleaned, page=i))
        return stream

    # peeks at whether the table is introductory/summary (okpd2, prohibitions, ktru).
    def _is_ignored_table(self, table_rows: List[List[str]]) -> bool:
        if not table_rows: 
            return True
            
        # we take the first 5 rows to analyze the table header and remove line breaks
        header_text = " ".join([" ".join(str(c).lower().replace('\n', ' ') for c in row) for row in table_rows[:5]])
        
        # strict specification table markers
        good_keywords = ["характеристик", "показател", "описание", "комплектация", "значени", "наименование товара", "параметр"]
        has_good_keywords = any(kw in header_text for kw in good_keywords)
        
        # pivot table markers (okpd2)
        bad_keywords = ["окпд", "ктру", "национальный режим", "запрет", "нмцк", "начальная цена", "ограничение"]
        
        # if there are safe words and there are no obvious signs of the specification - in the trash
        if any(kw in header_text for kw in bad_keywords) and not has_good_keywords:
            return True
            
        # if the "table" consists of only 1 column (it's just a paragraph of text that has mistakenly become a table)
        max_cols = max(len(row) for row in table_rows)
        if max_cols < 2:
            return True
            
        return False

    # groups blocks by cutting tables by position numbers in the first column.
    def group_stream_by_items(self, stream: List[ContentBlock]) -> List[List[ContentBlock]]:
        chunks = []
        current_chunk = []
        
        # strict regularity: the cell must contain only a number (and a possible dot/sign no.).
        item_pattern = re.compile(r'^\s*(?:№\s*)?(\d+)\.?\s*$')
        current_item_id = 0
        tz_ended = False
        
        # markers after which the tk is guaranteed to end and the contract begins
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
                
                # --- smart filtration ---
                if self._is_ignored_table(table_rows):
                    logger.info(f"⏭️ Пропущена таблица на стр. {block.page} (сводная таблица ОКПД2)")
                    continue

                last_split_idx = 0
                table_header = []
                
                for idx, row in enumerate(table_rows):
                    if not row or not row[0]:
                        continue
                        
                    # proactive protection: we check whether the terms of the contract have started
                    if current_item_id > 0:
                        # we take the first two columns and clear them of numbering (for example, “2nd place of delivery” -> “place of delivery”)
                        text = " ".join(str(c).lower() for c in row[:2])
                        text_clean = re.sub(r'^\s*(?:№\s*)?(?:\d+\.)*\d+\.?\s*', '', text).strip()
                        
                        if any(text_clean.startswith(m) for m in contract_markers):
                            logger.info(f"🛑 Обнаружен пункт договора ('{text_clean[:20]}...'). ТЗ завершено.")
                            tz_ended = True
                            # we cut off and save everything useful up to this point
                            if idx > last_split_idx:
                                old_part = table_rows[last_split_idx:idx]
                                current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                            break
                        
                    val = str(row[0]).strip()
                    match = item_pattern.match(val)
                    
                    if match:
                        num = int(match.group(1))
                        
                        # protection: the number must increase, and the table row must have at least 2 columns
                        if num > current_item_id and len(row) > 1:
                            # 1. cut off the old piece
                            if idx > last_split_idx:
                                old_part = table_rows[last_split_idx:idx]
                                
                                if current_item_id == 0:
                                    current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                                    table_header = old_part 
                                else:
                                    current_chunk.append(ContentBlock(type="table", content=old_part, page=block.page))
                            
                            # 2. close the chunk
                            if current_item_id > 0:
                                chunks.append(current_chunk)
                                current_chunk = []
                                # returning the cap for the next cut piece
                                if table_header:
                                    current_chunk.append(ContentBlock(type="table", content=table_header, page=block.page))
                                    
                            last_split_idx = idx
                            current_item_id = num
                
                # if parsing was interrupted by the terms of the contract, exit table processing
                if tz_ended:
                    break
                
                # add the remaining part (tail)
                remaining_part = table_rows[last_split_idx:]
                if remaining_part:
                    current_chunk.append(ContentBlock(type="table", content=remaining_part, page=block.page))
                
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

# description: function blocks_to_markdown. args: self, blocks. returns: str.
    def blocks_to_markdown(self, blocks: List[ContentBlock]) -> str:
        md = []
        for b in blocks:
            if b.type == "table":
                md.append(f"\n[Таблица, стр {b.page}]:\n{self._table_to_markdown(b.content)}")
        return "\n".join(md)

# description: function _table_to_markdown. args: self, table. returns: str.
    def _table_to_markdown(self, table: List[List[str]]) -> str:
        if not table: return ""
        processed_table = []
        for row in table:
            # glue empty cells (if the line has been moved)
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