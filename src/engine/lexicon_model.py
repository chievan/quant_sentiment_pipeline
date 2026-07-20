import re
from typing import Tuple, List

# High-accuracy financial dictionaries
CHINESE_FIN_LEXICON = {
    "positive": [
        "流入", "吸金", "大涨", "暴涨", "飙升", "突破", "买入", "上涨", "增持", "利好", 
        "扩产", "反弹", "新高", "突围", "过会", "IPO", "独苗", "爆发", "认购", "回暖", 
        "复苏", "净流入", "买超", "估值走高", "业绩超预期", "增长", "高增", "领跑", 
        "加仓", "配置", "获批", "好转", "升温", "坚挺", "提振"
    ],
    "negative": [
        "流出", "大跌", "暴跌", "降温", "踩踏", "赎回", "双杀", "折损", "踏空", "爆仓", 
        "回撤", "流失", "违规", "警示", "处罚", "缩减", "大挫", "崩盘", "折断", "亏损", 
        "失效", "崩溃", "下行", "减少", "滑坡", "爆雷", "清盘", "跑路", "净流出", "卖超", 
        "承压", "恶化", "走弱", "警惕", "砍单", "减持", "收紧", "退潮", "清仓", "违约"
    ]
}

ENGLISH_FIN_LEXICON = {
    "positive": [
        "growth", "stimulate", "safety", "success", "benefit", "improved", 
        "surpassed", "rise", "gain", "increase", "rebound", "soar", "profit", 
        "bullish", "upgrade", "outperform", "buy", "expansion", "dividend", 
        "positive", "exceeded", "advancing", "robust", "strong", "recovery"
    ],
    "negative": [
        "debt", "liabilities", "decline", "cut", "plummeted", "investigation", 
        "reduction", "drop", "loss", "deficit", "decrease", "risk", "fall", 
        "bearish", "downgrade", "underperform", "sell", "contraction", "shortage", 
        "negative", "missed", "declining", "weak", "concern", "warned", "slump"
    ]
}

class LexiconModel:
    def __init__(self):
        self.zh_lexicon = CHINESE_FIN_LEXICON
        self.en_lexicon = ENGLISH_FIN_LEXICON

    def _is_chinese(self, text: str) -> bool:
        """Heuristic check if the text contains Chinese characters."""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def score(self, text: str) -> Tuple[float, str]:
        """
        Calculates lexicon-based sentiment score (-1.0 to 1.0) and returns the channel name.
        Formula: (Positive_Words - Negative_Words) / (Positive_Words + Negative_Words)
        """
        if not text or len(text.strip()) == 0:
            return 0.0, "Lexicon-Neutral"
            
        text_lower = text.lower()
        is_zh = self._is_chinese(text)
        lexicon = self.zh_lexicon if is_zh else self.en_lexicon
        
        pos_words = [word for word in lexicon["positive"] if word in text_lower]
        neg_words = [word for word in lexicon["negative"] if word in text_lower]
        
        pos_count = len(pos_words)
        neg_count = len(neg_words)
        total = pos_count + neg_count
        
        if total == 0:
            return 0.0, "Lexicon-Neutral"
            
        score = (pos_count - neg_count) / total
        channel = "FinNLP-Lexicon-ZH" if is_zh else "FinNLP-Lexicon-EN"
        return round(score, 4), channel
