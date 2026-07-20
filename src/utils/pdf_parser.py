import os
import requests
import json
import io
import re

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

class PDFParser:
    def __init__(self, cache_path):
        self.cache_path = cache_path
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
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[PDFParser] Error saving cache: {e}")

    def extract_text_from_url(self, url, max_pages=2, max_chars=500):
        """Downloads a PDF and extracts text from the first few pages with caching."""
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
            # Stream download or read content directly
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
            cleaned_text = re.sub(r'\s+', ' ', extracted_text).strip()
            summary = cleaned_text[:max_chars]

            if len(summary) > 20:
                self.cache[url] = summary
                self._save_cache()
                return summary
            else:
                print(f"[PDFParser] Extracted text from {url} is too short or empty.")
        except Exception as e:
            print(f"[PDFParser] Error parsing PDF {url}: {e}")

        return ""
