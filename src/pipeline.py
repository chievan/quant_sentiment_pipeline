# Clear environment proxies to prevent proxy blockages on the server
import os
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    if key in os.environ:
        del os.environ[key]

import json
import pandas as pd
from datetime import datetime

# Add local path to import submodules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pdf_parser import PDFParser
from ingestion.rss_scraper import RSSScraper
from ingestion.ddb_extractor import DDBExtractor
from engine.lexicon_model import LexiconModel
from engine.bert_model import BERTModel
from engine.gemini_model import GeminiModel

def load_settings():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "config", 
        "settings.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Pipeline] Failed to load configuration: {e}")
        # Default fallback
        return {
            "dolphindb": {"host": "106.54.219.69", "port": 8848, "userid": "admin", "password": "123456"},
            "rsshub": {"base_url": "http://106.54.219.69:1200", "timeout": 15},
            "pipeline": {
                "output_dir": "/Users/chievan/Documents/projects/quant_sentiment_pipeline/data/factors",
                "pdf_cache_file": "/Users/chievan/Documents/projects/quant_sentiment_pipeline/data/pdf_cache.json",
                "articles_limit_per_feed": 20
            }
        }

def main():
    print(f"============================================================")
    print(f"🚀 STARTING STANDALONE QUANT SENTIMENT PIPELINE RUN")
    print(f"⏰ Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"============================================================")
    
    # 1. Load configuration
    settings = load_settings()
    pipe_cfg = settings["pipeline"]
    rss_cfg = settings["rsshub"]
    ddb_cfg = settings["dolphindb"]
    
    # Ensure directories exist
    os.makedirs(pipe_cfg["output_dir"], exist_ok=True)
    
    # 2. Initialize engines
    pdf_parser = PDFParser(cache_path=pipe_cfg["pdf_cache_file"])
    rss_scraper = RSSScraper(base_url=rss_cfg["base_url"], timeout=rss_cfg["timeout"])
    ddb_extractor = DDBExtractor(
        host=ddb_cfg["host"], 
        port=ddb_cfg["port"], 
        userid=ddb_cfg["userid"], 
        password=ddb_cfg["password"]
    )
    
    lexicon_engine = LexiconModel()
    # Try loading cached models; if they are not cached, it will fall back gracefully to Lexicon
    bert_engine = BERTModel(local_files_only=True)
    # Instantiate GeminiModel in mock mode for testing without token consumption
    gemini_engine = GeminiModel(mock_mode=True)
    
    # 3. Aggregating news corpus
    all_news = []
    
    # WeChat
    wechat_articles = ddb_extractor.fetch_wechat_articles(limit=pipe_cfg["articles_limit_per_feed"])
    all_news.extend(wechat_articles)
    
    # RSS Feeds
    rss_articles = rss_scraper.fetch_all(pdf_parser=pdf_parser, limit=pipe_cfg["articles_limit_per_feed"])
    all_news.extend(rss_articles)
    
    total_agg = len(all_news)
    print(f"\n[Pipeline] Ingestion completed. Total articles: {total_agg}")
    
    if total_agg == 0:
        print("[Pipeline] No articles found. Pipeline exiting.")
        return
        
    # 4. Scoring loop
    print("\n[Pipeline] Running scoring models...")
    scored_records = []
    
    for idx, item in enumerate(all_news):
        text = f"{item['title']} {item['summary']}"
        
        # Scoring with lexicon
        score_lexicon, channel_lexicon = lexicon_engine.score(text)
        
        # Scoring with BERT
        score_bert, channel_bert = bert_engine.score(text)
        
        # Scoring with Gemini
        score_gemini, channel_gemini = gemini_engine.score(text)
        
        # Format record
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pub_date": item["pubDate"],
            "source": item["source"],
            "title": item["title"],
            "link": item["link"],
            "score_finnlp": score_lexicon,
            "channel_finnlp": channel_lexicon,
            "score_finbert": score_bert if score_bert is not None else 0.0,
            "channel_finbert": channel_bert,
            "score_gemini": score_gemini,
            "channel_gemini": channel_gemini
        }
        scored_records.append(record)
        
        if (idx + 1) % 50 == 0 or (idx + 1) == total_agg:
            print(f"  Scored {idx + 1}/{total_agg} articles...")
            
    # 5. Save results to monthly CSV file
    df = pd.DataFrame(scored_records)
    
    file_name = f"sentiment_factors_{datetime.now().strftime('%Y%m')}.csv"
    output_path = os.path.join(pipe_cfg["output_dir"], file_name)
    
    # Append if exists, otherwise write header
    if os.path.exists(output_path):
        try:
            df.to_csv(output_path, mode='a', header=False, index=False, encoding='utf-8-sig')
            print(f"\n[Pipeline] Appended results to existing file: {output_path}")
        except Exception as e:
            print(f"\n[Pipeline] Failed to append, writing new file: {e}")
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n[Pipeline] Generated new factors CSV file: {output_path}")
        
    print(f"============================================================")
    print(f"🏁 PIPELINE RUN COMPLETED SUCCESSFULLY")
    print(f"📊 Total Records Generated: {len(df)}")
    print(f"============================================================")

if __name__ == "__main__":
    main()
