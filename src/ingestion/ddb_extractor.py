import requests
import json
import os
import re
import pandas as pd
from typing import List, Dict, Any

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>|&([a-z0-9]+|#[0-9]+|#x[0-9a-f]+);')
    return re.sub(cleanr, '', raw_html).strip()

class DDBExtractor:
    def __init__(self, host: str = "106.54.219.69", port: int = 8001, userid: str = "", password: str = "", db_path: str = "", table_name: str = ""):
        self.wemp_api_url = f"http://{host}:8001/api/v1/wx/articles"
        self.auth_token = "AK-SK WKG_sFGHG5wxDsKXhldZJ4LYkAXB_PogVN:SKC16vuOmWLCunEm1yW1w9L2hRzBTFaUgh"
        self.host = host
        self.port = 8848

    def fetch_wechat_articles(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetches WeChat Official Account articles directly from 106.54.219.69:8001 we-mp-rss API."""
        print(f"[WeChatExtractor] Fetching WeChat articles from 106 server 8001 API: {self.wemp_api_url}...")
        headers = {
            "Authorization": self.auth_token,
            "Content-Type": "application/json"
        }
        params = {
            "limit": limit,
            "offset": 0
        }
        
        articles = []
        try:
            r = requests.get(self.wemp_api_url, headers=headers, params=params, timeout=12)
            if r.status_code == 200:
                data = r.json()
                if "data" in data and "list" in data["data"]:
                    items = data["data"]["list"]
                    print(f"[WeChatExtractor] Successfully fetched {len(items)} WeChat articles from 8001 we-mp-rss!")
                    
                    for item in items:
                        title = item.get("title", "").strip()
                        mp_name = item.get("mp_name", "").strip() or "微信公众号"
                        url = item.get("url", "").strip()
                        pub_time = item.get("publish_time", "")
                        
                        raw_content = item.get("content", "") or item.get("description", "")
                        content = clean_html(raw_content)
                        
                        articles.append({
                            "id": item.get("id", ""),
                            "title": title if title else "无标题",
                            "summary": content if content else "无正文内容",
                            "pubDate": pub_time,
                            "link": url,
                            "source": f"微信公众号-{mp_name}",
                            "mp_name": mp_name
                        })
                    return articles
            print(f"[WeChatExtractor] 8001 API returned status {r.status_code}. Falling back to DolphinDB...")
        except Exception as e:
            print(f"[WeChatExtractor] 8001 API error: {e}. Falling back to DolphinDB...")
            
        # Fallback to DolphinDB if 8001 API fails
        return self._fetch_from_dolphindb(limit)

    def _fetch_from_dolphindb(self, limit: int = 25) -> List[Dict[str, Any]]:
        import dolphindb as ddb
        print(f"[WeChatExtractor] Connecting to DolphinDB fallback: {self.host}:{self.port}...")
        s = ddb.session()
        try:
            s.connect(self.host, self.port, "admin", "123456")
            s.run("use privateFundPro::market_news")
            res = s.run(f'get_articles_data(mp_id_str="all", page=1, page_size={limit})')
            articles = []
            if isinstance(res, dict) and "articles" in res:
                df = res["articles"]
                if hasattr(df, "toDF"):
                    df = df.toDF()
                df.columns = [col.lower() for col in df.columns]
                for _, row in df.iterrows():
                    mp_name = str(row.get("mp_name", "")).strip() or "微信公众号"
                    articles.append({
                        "id": str(row.get("id", "")),
                        "title": str(row.get("title", "")).strip(),
                        "summary": str(row.get("description", "")).strip(),
                        "pubDate": str(row.get("publish_time", "")),
                        "link": str(row.get("url", "")).strip(),
                        "source": f"微信公众号-{mp_name}",
                        "mp_name": mp_name
                    })
            return articles
        except Exception as e:
            print(f"[WeChatExtractor] DolphinDB fallback error: {e}")
            return []
        finally:
            s.close()
