import os
import requests
import json
import io
import re
import threading

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

class PDFParser:
    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.lock = threading.Lock()
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[PDFParser] Error loading cache: {e}")
        return {}

    def _save_cache(self):
        with self.lock:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            try:
                # Make a shallow copy to prevent runtime dict size mutation during JSON dump
                cache_copy = dict(self.cache)
                with open(self.cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache_copy, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[PDFParser] Error saving cache: {e}")

    def _llm_clean_pdf(self, raw_text: str) -> str:
        """Use Volcengine LLM to clean noisy PDF text, stripping disclaimers and extracting core research takeaways."""
        if not raw_text or len(raw_text.strip()) < 15:
            return ""
            
        api_base = os.getenv("VOLC_API_BASE") or os.getenv("OPENAI_API_BASE") or "https://ark.cn-beijing.volces.com/api/plan/v3"
        api_key = os.getenv("VOLC_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            local_settings_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "config", "settings_local.json"
            )
            if os.path.exists(local_settings_path):
                try:
                    with open(local_settings_path, "r", encoding="utf-8") as f:
                        api_key = json.load(f).get("volc_api_key")
                except Exception:
                    pass
                    
        if not api_key:
            return raw_text[:500]  # Fallback to truncated raw text
            
        url = f"{api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        prompt = (
            "你是一个专业的券商研报文本精炼助手。以下是从券商 PDF 研报中提炼出的文本（可能包含大量免责声明、分析师署名、杂乱代码或格式破损）。\n"
            "请彻底剔除所有免责声明、分析师联系方式和格式乱码，仅保留并重构该研报的核心投资逻辑、观点与重要数据，用一段 200 字以内的通顺摘要输出：\n\n"
            f"原始PDF文本：\n{raw_text[:2500]}"
        )
        payload = {
            "model": "doubao-seed-2.0-lite",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 300
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=12)
            if r.status_code == 200:
                cleaned = r.json()["choices"][0]["message"]["content"].strip()
                if cleaned:
                    return cleaned
        except Exception as e:
            print(f"[PDFParser] LLM PDF clean error: {e}")
            
        return raw_text[:500]

    def extract_text_from_url(self, url, max_pages=3, max_chars=500):
        """Downloads a PDF and extracts text from the first few pages, refined by LLM if needed."""
        with self.lock:
            if url in self.cache:
                return self.cache[url]

        if not PYPDF_AVAILABLE:
            print("[PDFParser] Warning: pypdf library is not installed. Skipping PDF parse.")
            return ""

        print(f"[PDFParser] Downloading & parsing PDF: {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            r = requests.get(url, headers=headers, timeout=20, proxies={"http": None, "https": None})
            if r.status_code != 200:
                print(f"[PDFParser] Failed to download PDF. Status: {r.status_code}")
                return ""

            pdf_file = io.BytesIO(r.content)
            reader = pypdf.PdfReader(pdf_file)
            
            extracted_text = ""
            # Extract from first max_pages
            for i in range(min(max_pages, len(reader.pages))):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    extracted_text += page_text + "\n"

            # Clean and normalize text
            cleaned_raw = re.sub(r'\s+', ' ', extracted_text).strip()
            
            # Smart check: If text is present, pass to LLM to strip disclaimers and extract core research summary
            if len(cleaned_raw) > 20:
                print(f"[PDFParser] Refining PDF text via LLM for {url[:50]}...")
                final_summary = self._llm_clean_pdf(cleaned_raw)
                
                with self.lock:
                    self.cache[url] = final_summary
                self._save_cache()
                return final_summary
            else:
                print(f"[PDFParser] Extracted text from {url} is too short or empty.")
        except Exception as e:
            print(f"[PDFParser] Error parsing PDF {url}: {e}")

        return ""
