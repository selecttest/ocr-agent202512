"""
通用文件 OCR 模組 - 精簡輸出版本
"""

import vertexai
from vertexai.generative_models import GenerativeModel, Part
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging
import fitz  # PyMuPDF
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DocumentResult:
    success: bool
    total_pages: int
    detected_type: str
    language: str
    blocks: List[Dict]
    full_text: str
    key_value_pairs: List[Dict]
    tables: List[Dict]
    images_summary: Optional[Any] = None
    processing_time: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class UniversalOCRAgent:
    
    SYSTEM_PROMPT = """你是專業的文件分析系統。請完整提取文件中的所有重要資訊，包括表格每一列數據、圖片中的所有文字標註。輸出必須是有效的 JSON。"""

    EXTRACTION_PROMPT = """仔細分析 PDF 第 {start_page}-{end_page} 頁的所有內容，完整提取所有文字資訊，輸出 JSON。

格式：
{{
  "detected_type": "文件類型",
  "language": "zh-TW",
  "blocks": [
    {{"id": "b1", "type": "類型", "page": 1, "region": "位置", "content": "完整內容文字"}}
  ],
  "key_value_pairs": [{{"key": "欄位名稱", "value": "欄位值", "page": 1}}],
  "tables": [{{"id": "t1", "page": 1, "summary": "表格標題", "data": "完整表格內容"}}],
  "images": [{{"id": "i1", "type": "類型", "page": 1, "description": "圖片完整描述"}}],
  "summary": "文件完整摘要"
}}

類型：photo/logo/chart/figure/header/section_title/text/list/table/form_field/map/diagram
位置：左上/中上/右上/左中/中央/右中/左下/中下/右下

【重要規則 - 務必遵守】：

1. **表格處理**：
   - tables.data 必須包含表格的【完整內容】，每一列都要提取
   - 格式範例：「1.南港昆陽置地廣場停車場 2.南港遠東智慧科學園區管理委員會停車場 3.玉成國小地下停車場...」
   - 不要只寫摘要，要列出所有數據

2. **圖片/地圖處理**：
   - 提取圖片中所有可見的文字標註、地名、路名、標記
   - images.description 要詳細描述圖片內容和所有文字

3. **內容提取**：
   - blocks.content 必須包含完整文字，不可截斷或省略
   - 每頁的所有文字區塊都要提取，不限數量

4. **key_value_pairs**：
   - 從表格和內容中提取所有重要的鍵值對
   - 例如：停車場資訊要提取「編號1」:「南港昆陽置地廣場停車場」

5. **summary**：
   - 摘要要包含具體資訊，不要只說「提到了XXX」
   - 要說明具體有哪些內容

只輸出 JSON，不要其他文字"""

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        max_output_tokens: int = 8192
    ):
        self.project_id = project_id
        self.location = location
        
        logger.info(f"初始化 Vertex AI: project={project_id}, location={location}")
        vertexai.init(project=project_id, location=location)
        
        self.model = GenerativeModel(
            model_name,
            system_instruction=self.SYSTEM_PROMPT
        )
        
        self.generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens
        }
        
        logger.info("OCR Agent 初始化完成")

    def _get_batch_size(self, total_pages: int) -> int:
        """根據總頁數決定每批處理的頁數 - 更保守的設定"""
        if total_pages <= 10:
            return total_pages
        elif total_pages <= 30:
            return 5
        elif total_pages <= 100:
            return 8
        else:
            return 10  # 大文件每批最多10頁

    def _split_pdf(self, pdf_data: bytes, start_page: int, end_page: int) -> bytes:
        """擷取 PDF 的指定頁面範圍"""
        src_doc = fitz.open(stream=pdf_data, filetype="pdf")
        new_doc = fitz.open()
        
        for page_num in range(start_page - 1, min(end_page, len(src_doc))):
            new_doc.insert_pdf(src_doc, from_page=page_num, to_page=page_num)
        
        pdf_bytes = new_doc.tobytes()
        new_doc.close()
        src_doc.close()
        
        return pdf_bytes

    def _get_pdf_page_count(self, pdf_data: bytes) -> int:
        """取得 PDF 頁數"""
        try:
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"取得頁數失敗: {e}")
            return 1
    
    def _fix_page_numbers(self, result: Dict, page_offset: int):
        """修正批次處理後的頁碼
        
        Args:
            result: 批次處理的結果
            page_offset: 頁碼偏移量（原始起始頁 - 1）
        """
        if page_offset == 0:
            return  # 不需要修正
        
        # 修正 blocks 的頁碼
        for block in result.get("blocks", []):
            if "page" in block and isinstance(block["page"], int):
                block["page"] += page_offset
        
        # 修正 key_value_pairs 的頁碼
        for kv in result.get("key_value_pairs", []):
            if "page" in kv and isinstance(kv["page"], int):
                kv["page"] += page_offset
        
        # 修正 tables 的頁碼
        for table in result.get("tables", []):
            if "page" in table and isinstance(table["page"], int):
                table["page"] += page_offset
        
        # 修正 images 的頁碼
        for img in result.get("images", []):
            if "page" in img and isinstance(img["page"], int):
                img["page"] += page_offset

    def _process_batch(self, pdf_data: bytes, start_page: int, end_page: int) -> Dict:
        """處理單一批次"""
        prompt = self.EXTRACTION_PROMPT.format(
            start_page=start_page,
            end_page=end_page
        )
        
        pdf_part = Part.from_data(data=pdf_data, mime_type="application/pdf")
        
        response = self.model.generate_content(
            [pdf_part, prompt],
            generation_config=self.generation_config
        )
        
        return self._parse_response(response.text)

    def _merge_results(self, results: List[Dict], total_pages: int) -> Dict:
        """合併多批次的結果"""
        merged = {
            "detected_type": "",
            "language": "",
            "total_pages": total_pages,
            "blocks": [],
            "key_value_pairs": [],
            "tables": [],
            "images_summary": {
                "total_count": 0,
                "items": []
            },
            "text_summary": ""
        }
        
        summaries = []
        block_counter = 1
        table_counter = 1
        image_counter = 1
        
        for result in results:
            if not merged["detected_type"] and result.get("detected_type"):
                merged["detected_type"] = result["detected_type"]
            if not merged["language"] and result.get("language"):
                merged["language"] = result["language"]
            
            # 合併 blocks
            for block in result.get("blocks", []):
                block["id"] = f"block_{block_counter:03d}"
                block_counter += 1
                merged["blocks"].append(block)
            
            # 合併 key_value_pairs
            merged["key_value_pairs"].extend(result.get("key_value_pairs", []))
            
            # 合併 tables
            for table in result.get("tables", []):
                table["id"] = f"table_{table_counter:03d}"
                table_counter += 1
                merged["tables"].append(table)
            
            # 合併 images
            images = result.get("images", [])
            if images:
                for img in images:
                    img["id"] = f"img_{image_counter:03d}"
                    image_counter += 1
                    merged["images_summary"]["items"].append(img)
                merged["images_summary"]["total_count"] += len(images)
            
            # 收集摘要
            if result.get("summary"):
                summaries.append(result["summary"])
        
        merged["text_summary"] = " | ".join(summaries[:10])  # 最多保留10個摘要
        
        return merged

    def process_file(self, pdf_path: str) -> DocumentResult:
        logger.info(f"處理檔案: {pdf_path}")
        try:
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            return self._process(pdf_data)
        except FileNotFoundError:
            return self._error_result(f"檔案不存在: {pdf_path}")
        except Exception as e:
            return self._error_result(str(e))

    def process_bytes(self, pdf_data: bytes) -> DocumentResult:
        logger.info(f"處理 bytes 資料，大小: {len(pdf_data)} bytes")
        return self._process(pdf_data)

    def process_gcs(self, bucket: str, blob_name: str) -> DocumentResult:
        logger.info(f"處理 GCS 檔案: gs://{bucket}/{blob_name}")
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(blob_name)
            pdf_data = blob.download_as_bytes()
            return self._process(pdf_data)
        except Exception as e:
            return self._error_result(str(e))

    def _process(self, pdf_data: bytes) -> DocumentResult:
        try:
            start_time = time.time()
            
            # 取得總頁數
            total_pages = self._get_pdf_page_count(pdf_data)
            logger.info(f"PDF 總頁數: {total_pages}")
            
            # 決定批次大小
            batch_size = self._get_batch_size(total_pages)
            logger.info(f"批次大小: {batch_size} 頁")
            
            # 如果可以一次處理完
            if batch_size >= total_pages:
                logger.info("單次處理全部頁面")
                result = self._process_batch(pdf_data, 1, total_pages)
                
                elapsed = time.time() - start_time
                processing_time = {
                    "total_seconds": round(elapsed, 2),
                    "total_formatted": self._format_time(elapsed),
                    "batch_count": 1
                }
                
                # 處理 images
                images_summary = None
                if result.get("images"):
                    images_summary = {
                        "total_count": len(result["images"]),
                        "items": result["images"]
                    }
                
                return DocumentResult(
                    success=True,
                    total_pages=total_pages,
                    detected_type=result.get("detected_type", "unknown"),
                    language=result.get("language", "unknown"),
                    blocks=result.get("blocks", []),
                    full_text=result.get("summary", ""),
                    key_value_pairs=result.get("key_value_pairs", []),
                    tables=result.get("tables", []),
                    images_summary=images_summary,
                    processing_time=processing_time
                )
            
            # 分批處理
            results = []
            batch_info = []  # 記錄每個批次的起始頁碼
            batch_num = 0
            successful_batches = 0
            failed_batches = 0
            
            for start in range(1, total_pages + 1, batch_size):
                end = min(start + batch_size - 1, total_pages)
                batch_num += 1
                logger.info(f"處理第 {start} - {end} 頁（批次 {batch_num}）...")
                
                # 擷取該範圍的頁面
                batch_pdf = self._split_pdf(pdf_data, start, end)
                
                # 處理這批（最多重試2次）
                for attempt in range(2):
                    try:
                        # 注意：分割後的 PDF 頁碼從 1 開始，但我們需要告訴 AI 原始頁碼範圍
                        batch_result = self._process_batch(batch_pdf, 1, end - start + 1)
                        
                        # 修正頁碼：將返回的頁碼轉換為原始 PDF 頁碼
                        page_offset = start - 1
                        self._fix_page_numbers(batch_result, page_offset)
                        
                        results.append(batch_result)
                        batch_info.append({"start": start, "end": end})
                        successful_batches += 1
                        logger.info(f"第 {start} - {end} 頁處理完成")
                        break
                    except Exception as e:
                        if attempt == 1:  # 第二次失敗
                            logger.error(f"第 {start} - {end} 頁處理失敗: {e}")
                            failed_batches += 1
                        else:
                            logger.warning(f"第 {start} - {end} 頁第一次嘗試失敗，重試中...")
            
            if not results:
                return self._error_result("所有批次處理都失敗")
            
            # 合併結果
            logger.info(f"合併結果：成功 {successful_batches} 批，失敗 {failed_batches} 批")
            merged = self._merge_results(results, total_pages)
            
            elapsed = time.time() - start_time
            processing_time = {
                "total_seconds": round(elapsed, 2),
                "total_formatted": self._format_time(elapsed),
                "batch_count": batch_num,
                "successful_batches": successful_batches,
                "failed_batches": failed_batches
            }
            
            return DocumentResult(
                success=True,
                total_pages=total_pages,
                detected_type=merged.get("detected_type", "unknown"),
                language=merged.get("language", "unknown"),
                blocks=merged.get("blocks", []),
                full_text=merged.get("text_summary", ""),
                key_value_pairs=merged.get("key_value_pairs", []),
                tables=merged.get("tables", []),
                images_summary=merged.get("images_summary", None),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"處理錯誤: {str(e)}")
            return self._error_result(str(e))

    def _format_time(self, seconds: float) -> str:
        """將秒數格式化為易讀格式"""
        if seconds < 60:
            return f"{round(seconds, 1)} 秒"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins} 分 {secs} 秒"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours} 小時 {mins} 分"

    def _parse_response(self, text: str) -> Dict:
        cleaned = text.strip()
        
        # 移除 markdown 標記
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # 嘗試直接解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # 嘗試修復不完整的 JSON
        logger.warning("JSON 可能不完整，嘗試修復...")
        
        # 找到最後一個有效的位置
        for end_pos in range(len(cleaned), 0, -1):
            test_str = cleaned[:end_pos]
            
            # 補上缺少的括號
            open_braces = test_str.count("{") - test_str.count("}")
            open_brackets = test_str.count("[") - test_str.count("]")
            
            if open_braces >= 0 and open_brackets >= 0:
                fixed = test_str + "]" * open_brackets + "}" * open_braces
                try:
                    return json.loads(fixed)
                except:
                    continue
        
        raise json.JSONDecodeError("無法修復 JSON", cleaned, 0)

    def _error_result(self, error_msg: str) -> DocumentResult:
        return DocumentResult(
            success=False, total_pages=0, detected_type="", language="",
            blocks=[], full_text="", key_value_pairs=[], tables=[],
            images_summary=None, processing_time=None, error=error_msg
        )


def quick_ocr(project_id: str, pdf_path: str) -> Dict:
    agent = UniversalOCRAgent(project_id=project_id)
    result = agent.process_file(pdf_path)
    return result.to_dict()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("使用方式: python ocr_agent.py <project_id> <pdf_path>")
        sys.exit(1)
    result = quick_ocr(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
