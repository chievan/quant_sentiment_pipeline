import os
import re
from typing import Tuple, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiModel:
    def __init__(self, api_key: str = None, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = None
        self.channel_name = "Gemini-Mock" if mock_mode else "Gemini-API"

        if not self.mock_mode:
            if not self.api_key:
                print("[GeminiModel] Warning: No API Key provided and mock_mode=False. Falling back to Mock mode.")
                self.mock_mode = True
                self.channel_name = "Gemini-Mock (Fallback)"
            elif not GENAI_AVAILABLE:
                print("[GeminiModel] Warning: google-generativeai is not installed. Falling back to Mock mode.")
                self.mock_mode = True
                self.channel_name = "Gemini-Mock (Fallback)"
            else:
                try:
                    genai.configure(api_key=self.api_key)
                    # Using gemini-1.5-flash which is fast and cost-effective for scoring
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
                    print("[GeminiModel] Successfully initialized real Gemini API connection.")
                except Exception as e:
                    print(f"[GeminiModel] Initialization error: {e}. Falling back to Mock mode.")
                    self.mock_mode = True
                    self.channel_name = "Gemini-Mock (Fallback)"

    def score(self, text: str) -> Tuple[Optional[float], str]:
        """
        Calculates sentiment score using Gemini.
        Returns (score, channel_name).
        Score is a float between -1.0 (extreme negative) and 1.0 (extreme positive).
        """
        if not text or len(text.strip()) == 0:
            return 0.0, self.channel_name

        if self.mock_mode:
            return self._mock_score(text), self.channel_name
        else:
            return self._real_score(text), self.channel_name

    def _mock_score(self, text: str) -> float:
        """A simple zero-cost mock scoring algorithm based on keyword matching."""
        text_lower = text.lower()
        pos_words = ["涨", "利好", "增长", "突破", "买入", "增持", "飙升", "复苏", "牛市", "升温"]
        neg_words = ["跌", "利空", "亏损", "下滑", "卖出", "减持", "暴跌", "衰退", "熊市", "降温"]
        
        pos_count = sum(1 for w in pos_words if w in text_lower)
        neg_count = sum(1 for w in neg_words if w in text_lower)
        
        if pos_count == 0 and neg_count == 0:
            return 0.0
            
        score = (pos_count - neg_count) / (pos_count + neg_count)
        return round(score, 4)

    def _real_score(self, text: str) -> float:
        """Call the actual Gemini API to score the sentiment."""
        prompt = f"""
        你是一位专业的量化金融分析师。请分析以下财经资讯内容，判断其对相关资产价格的情绪极性。
        请仅回复一个 -1.0 到 1.0 之间的浮点数。
        -1.0 代表极度负面（重大利空，强烈看跌）
        0.0 代表完全中性（无关痛痒，无增量信息）
        1.0 代表极度正面（重大利好，强烈看涨）
        
        待分析内容：
        {text}
        
        请直接输出数字，不要输出任何其他解释或文字。
        """
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract float from response using regex in case model outputs extra chars
            match = re.search(r'-?\d+\.\d+|-?\d+', result_text)
            if match:
                score = float(match.group())
                # Clamp score between -1.0 and 1.0
                score = max(-1.0, min(1.0, score))
                return score
            else:
                print(f"[GeminiModel] API returned unparsable response: '{result_text}'")
                return 0.0
        except Exception as e:
            print(f"[GeminiModel] API request failed: {e}")
            return 0.0
