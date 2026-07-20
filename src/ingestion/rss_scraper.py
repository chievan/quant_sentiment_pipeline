import requests
import xml.etree.ElementTree as ET
import re
import concurrent.futures
from typing import List, Dict, Any

class RSSScraper:
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        self.feeds = [
            {"source": "东方财富-宏观", "path": "eastmoney/report/macresearch"},
            {"source": "东方财富-策略", "path": "eastmoney/report/strategyreport"},
            {"source": "东方财富-券商晨报", "path": "eastmoney/report/brokerreport"},
            {"source": "东方财富-行业", "path": "eastmoney/report/industry"},
            {"source": "东方财富-个股", "path": "eastmoney/report/stock"},
            {"source": "财联社-热点", "path": "cls/hot"},
            {"source": "雪球热帖", "path": "xueqiu/hots"},
            {"source": "华尔街见闻-要闻", "path": "wallstreetcn/live/global"},
            {"source": "华尔街见闻-周热榜", "path": "wallstreetcn/hot/week"},
            {"source": "华尔街见闻-日历", "path": "wallstreetcn/calendar/macrodatas"},
            {"source": "麦肯锡-宏观", "path": "mckinsey/cn/macroeconomy"},
            {"source": "格隆汇-周热榜", "path": "gelonghui/hot-article/week"},
            {"source": "格隆汇-日热榜", "path": "gelonghui/hot-article/day"},
            {"source": "有知有行", "path": "youzhiyouxing/materials/0"},
            {"source": "BigQuant-研报", "path": "bigquant/collections"},
            {"source": "富途要闻", "path": "futunn/main"},
            {"source": "富途-AI专题", "path": "futunn/topic/1267"},
            {"source": "彭博新闻", "path": "bloomberg/%2F"}
        ]

    def _clean_html(self, text: str) -> str:
        if not text:
            return ""
        cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]+|#x[0-9a-f]+);')
        return re.sub(cleanr, '', text).strip()

    def fetch_feed(self, feed: Dict[str, str], pdf_parser: Any, limit: int = 20) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{feed['path']}"
        print(f"[RSSScraper] Fetching feed: {feed['source']} ({url})")
        articles = []
        try:
            r = requests.get(url, timeout=self.timeout, proxies={"http": None, "https": None})
            r.encoding = 'utf-8'
            if r.status_code != 200:
                print(f"[RSSScraper] Feed {feed['source']} failed with HTTP {r.status_code}")
                return []

            root = ET.fromstring(r.content)
            items = root.findall('.//item')
            for item in items[:limit]:
                title_node = item.find('title')
                title = title_node.text.strip() if title_node is not None and title_node.text is not None else ""
                
                link_node = item.find('link')
                link = link_node.text.strip() if link_node is not None and link_node.text is not None else ""
                
                desc_node = item.find('description')
                desc = desc_node.text.strip() if desc_node is not None and desc_node.text is not None else ""
                
                pub_date_node = item.find('pubDate')
                pub_date = pub_date_node.text.strip() if pub_date_node is not None and pub_date_node.text is not None else ""
                
                # Check for PDF link
                is_pdf = link.endswith(".pdf") or "pdf" in link.lower()
                summary = ""
                if is_pdf and pdf_parser:
                    summary = pdf_parser.extract_text_from_url(link)
                
                # Fallback to description
                if not summary:
                    summary = self._clean_html(desc)[:350]

                articles.append({
                    "title": title.strip() if title else "无标题",
                    "summary": summary.strip() if summary else "无摘要",
                    "pubDate": pub_date.strip() if pub_date else "",
                    "link": link.strip() if link else "",
                    "source": feed['source']
                })
            print(f"[RSSScraper] Loaded {len(articles)} articles from {feed['source']}.")
            return articles
        except Exception as e:
            print(f"[RSSScraper] Error fetching {feed['source']}: {e}")
            return []

    def fetch_all(self, pdf_parser: Any, limit: int = 20) -> List[Dict[str, Any]]:
        """Concurrently fetches all RSS feeds."""
        all_articles = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.fetch_feed, feed, pdf_parser, limit): feed
                for feed in self.feeds
            }
            for future in concurrent.futures.as_completed(futures):
                feed = futures[future]
                try:
                    results = future.result()
                    all_articles.extend(results)
                except Exception as e:
                    print(f"[RSSScraper] Feed {feed['source']} execution error: {e}")
        return all_articles
