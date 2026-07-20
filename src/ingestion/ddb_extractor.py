import dolphindb as ddb
import pandas as pd
from typing import List, Dict, Any

class DDBExtractor:
    def __init__(self, host: str, port: int, userid: str, password: str, db_path: str = "dfs://HAZQ.articles", table_name: str = "data"):
        self.host = host
        self.port = port
        self.userid = userid
        self.password = password
        self.db_path = db_path
        self.table_name = table_name

    def fetch_wechat_articles(self, limit: int = 50) -> List[Dict[str, Any]]:
        print(f"[DDBExtractor] Connecting to DolphinDB: {self.host}:{self.port}...")
        s = ddb.session()
        try:
            s.connect(self.host, self.port, self.userid, self.password)
            print("[DDBExtractor] Connected. Querying articles...")
            
            df = None
            # Try running the server-side module function first
            try:
                s.run("use privateFundPro::market_news")
                res = s.run(f'get_articles_data(mp_id_str="all", page=1, page_size={limit})')
                if isinstance(res, dict) and "articles" in res:
                    df = pd.DataFrame(res["articles"])
                elif isinstance(res, pd.DataFrame):
                    df = res
                else:
                    df = pd.DataFrame(res)
            except Exception as e:
                print(f"[DDBExtractor] Stored function query failed ({e}). Falling back to direct loadTable...")
                try:
                    query = f'select * from loadTable("{self.db_path}", "{self.table_name}") order by publish_time desc limit {limit}'
                    df = s.run(query)
                except Exception as inner_e:
                    print(f"[DDBExtractor] Direct loadTable query also failed: {inner_e}")
                    df = None

            articles = []
            if df is not None and not df.empty:
                # Normalize column names to lowercase for consistency
                df.columns = [col.lower() for col in df.columns]
                
                # Check for standard fields
                title_col = 'title' if 'title' in df.columns else (df.columns[0] if len(df.columns) > 0 else '')
                summary_col = 'summary' if 'summary' in df.columns else ('description' if 'description' in df.columns else '')
                date_col = 'publish_time' if 'publish_time' in df.columns else ('pub_date' if 'pub_date' in df.columns else '')
                url_col = 'url' if 'url' in df.columns else ('link' if 'link' in df.columns else '')

                for _, row in df.iterrows():
                    title = str(row.get(title_col, "")).strip() if title_col else ""
                    summary = str(row.get(summary_col, "")).strip() if summary_col else ""
                    pub_date = str(row.get(date_col, "")) if date_col else ""
                    url = str(row.get(url_col, "")).strip() if url_col else ""
                    
                    articles.append({
                        "title": title,
                        "summary": summary[:350],
                        "pubDate": pub_date,
                        "link": url,
                        "source": "微信公众号"
                    })
            print(f"[DDBExtractor] Successfully parsed {len(articles)} WeChat articles.")
            return articles
        except Exception as e:
            print(f"[DDBExtractor] DolphinDB connection or query error: {e}")
            return []
        finally:
            s.close()
