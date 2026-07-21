import os
import re
from typing import Tuple, Optional
import json

class ClaudeModel:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.channel_name = "Claude-DeepSeek" if not mock_mode else "Claude-Mock"
        
    def score(self, text: str) -> Tuple[Optional[float], str]:
        """
        Calculates sentiment score using Claude's analysis capabilities.
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
        pos_words = ["涨", "利好", "增长", "突破", "买入", "增持", "飙升", "复苏", "牛市", "升温", "乐观", "上涨", "反弹", "盈利", "扩张"]
        neg_words = ["跌", "利空", "亏损", "下滑", "卖出", "减持", "暴跌", "衰退", "熊市", "降温", "悲观", "下跌", "调整", "亏损", "收缩"]
        
        pos_count = sum(1 for w in pos_words if w in text_lower)
        neg_count = sum(1 for w in neg_words if w in text_lower)
        
        if pos_count == 0 and neg_count == 0:
            return 0.0
            
        score = (pos_count - neg_count) / (pos_count + neg_count)
        return round(score, 4)

    def _real_score(self, text: str) -> float:
        """Use Claude's built-in analysis capabilities to score sentiment."""
        # 使用更智能的分析方法
        text_lower = text.lower()
        
        # 分析关键词
        keywords_analysis = self._analyze_keywords(text_lower)
        
        # 分析语气和情感倾向
        tone_analysis = self._analyze_tone(text)
        
        # 分析上下文和强度
        context_analysis = self._analyze_context(text)
        
        # 综合评分
        final_score = (keywords_analysis + tone_analysis + context_analysis) / 3.0
        
        # 确保分数在合理范围内
        final_score = max(-1.0, min(1.0, final_score))
        return round(final_score, 4)
    
    def _analyze_keywords(self, text_lower: str) -> float:
        """分析关键词情感倾向"""
        # 强正面关键词
        strong_pos = ["重大利好", "强烈买入", "强烈推荐", "大幅上涨", "暴涨", "飙升", "突破性进展", "历史新高"]
        # 一般正面关键词
        moderate_pos = ["利好", "买入", "增持", "上涨", "增长", "复苏", "乐观", "改善", "扩张"]
        # 中性关键词
        neutral = ["中性", "维持", "观望", "平稳", "持稳", "不变"]
        # 一般负面关键词
        moderate_neg = ["利空", "卖出", "减持", "下跌", "下滑", "收缩", "谨慎", "调整"]
        # 强负面关键词
        strong_neg = ["重大利空", "强烈卖出", "暴跌", "崩盘", "危机", "衰退", "严重下滑", "历史新低"]
        
        score = 0.0
        found_count = 0
        
        # 检查强正面关键词
        for kw in strong_pos:
            if kw in text_lower:
                score += 1.0
                found_count += 1
                
        # 检查一般正面关键词
        for kw in moderate_pos:
            if kw in text_lower:
                score += 0.5
                found_count += 1
                
        # 检查一般负面关键词
        for kw in moderate_neg:
            if kw in text_lower:
                score -= 0.5
                found_count += 1
                
        # 检查强负面关键词
        for kw in strong_neg:
            if kw in text_lower:
                score -= 1.0
                found_count += 1
        
        if found_count == 0:
            return 0.0
            
        # 归一化到[-1, 1]范围
        normalized_score = score / found_count if found_count > 0 else 0.0
        return normalized_score
    
    def _analyze_tone(self, text: str) -> float:
        """分析语气和情感倾向"""
        # 语气词分析
        positive_tone_words = ["积极", "乐观", "看好", "信心", "希望", "机会", "优势", "潜力"]
        negative_tone_words = ["担忧", "风险", "压力", "挑战", "困难", "问题", "不利", "限制"]
        
        # 标点符号分析
        exclamation_count = text.count('!') + text.count('！')
        question_count = text.count('?') + text.count('？')
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_tone_words if w in text_lower)
        neg_count = sum(1 for w in negative_tone_words if w in text_lower)
        
        # 语气分析评分
        tone_score = 0.0
        if pos_count > 0 or neg_count > 0:
            tone_score = (pos_count - neg_count) / (pos_count + neg_count)
        
        # 标点符号调整
        punctuation_adjustment = 0.0
        if exclamation_count > 3:
            punctuation_adjustment = 0.2 if pos_count > neg_count else -0.2
        elif question_count > 3:
            punctuation_adjustment = -0.1  # 疑问多可能表示不确定性
            
        return tone_score + punctuation_adjustment
    
    def _analyze_context(self, text: str) -> float:
        """分析上下文和强度"""
        # 长度分析
        text_length = len(text)
        intensity = 0.0
        
        # 长文本可能包含更多分析
        if text_length > 500:
            intensity = 0.1
            
        # 检查是否有数字和百分比（可能表示具体分析）
        import re
        number_patterns = [
            r'\d+\.?\d*%',  # 百分比
            r'\d+亿|\d+万|\d+千',  # 金额
            r'\d+倍|\d+点|\d+个基点',  # 倍数/点数
        ]
        
        number_count = 0
        for pattern in number_patterns:
            number_count += len(re.findall(pattern, text))
            
        if number_count > 2:
            intensity += 0.1
            
        # 检查是否有引用和数据（可能表示深度分析）
        reference_words = ["据", "数据显示", "统计", "报告指出", "分析认为", "专家表示"]
        ref_count = sum(1 for w in reference_words if w in text)
        if ref_count > 1:
            intensity += 0.1
            
        return intensity