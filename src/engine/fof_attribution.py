import os
from typing import List, Dict, Any, Tuple

FOF_RULES = {
    "STYLE_FACTOR": {
        "keywords": ["大小盘", "微盘", "小市值", "小盘股", "大盘股", "权重股", "抱团", "红利", "风格切换", "因子拥挤", "超额回撤", "出清", "超调", "风格漂移", "中证500", "中证1000", "沪深300"],
        "name": "市场结构与风格因子",
        "description": "监控量化风格拥挤度、大小盘风格轮动（如沪深300 vs 中证1000/微盘股走势）、红利与科技因子漂移以及超额Alpha因子的偏离情况。"
    },
    "BETA_TIMING": {
        "keywords": ["大跌", "暴跌", "普跌", "跌停潮", "大涨", "暴涨", "普涨", "降息", "央行", "政策", "熔断", "崩盘", "去杠杆", "强平", "规划", "放缓", "牛市", "熊市", "降准", "MLF", "公开市场操作"],
        "name": "Beta 敞口与大势择时",
        "description": "监控系统性风险、宏观流动性信用扩张/收缩、市场极端情绪（如两市大跌/强平压力），辅助量化 FOF 决定是否临时调整 Beta 暴露。"
    },
    "HEDGE_COST": {
        "keywords": ["基差", "贴水", "股指期货", "对冲", "期权", "升水", "主力合约", "国债期货", "IC合约", "IM合约", "IF合约"],
        "name": "市场中性与对冲基差",
        "description": "监控股指期货（IC/IF/IM）基差贴水深度变化、对冲工具成本，防范基差贴水大幅波动对中性策略子基金造成的基差双杀。"
    },
    "HFT_REGULATION": {
        "keywords": ["高频", "T0", "换手", "成交额", "地量", "巨量", "程序化交易", "量化监管", "算法交易", "报单", "撤单", "交易规则", "万亿", "两市成交"],
        "name": "T0中性与高频流动性",
        "description": "监控全市场成交量级（地量/巨量临界点）、换手率以及高频程序化交易的监管风向，评估 T0中性 策略的超额阿尔法收益生存空间。"
    },
    "CTA_TREND": {
        "keywords": ["期货", "库存", "铜", "铝", "锌", "铅", "镍", "天然橡胶", "多晶硅", "钯", "黄金", "石油", "地缘", "伊朗", "油轮", "袭击", "地缘冲突", "中东"],
        "name": "CTA趋势与商品套利",
        "description": "监控商品期货大宗库存异动、地缘政治冲突对供应链的冲击，提供 CTA 管理人时序/截面动量或套利机会的配置信号。"
    }
}

class FOFAttributionEngine:
    def __init__(self):
        self.rules = FOF_RULES

    def clean_text(self, text: str) -> bool:
        """
        Returns True if the text is meaningful (not noise like empty posts or advertisements).
        """
        if not text or len(text.strip()) == 0:
            return False
        
        # Filter typical noise keywords
        noise_kws = ["无标题", "扫码加入", "广告", "转机", "客服"]
        for kw in noise_kws:
            if kw in text:
                return False
                
        # Filter very short texts
        if len(text.strip()) < 5:
            return False
            
        return True

    def attribute_article(self, text: str) -> List[Tuple[str, List[str]]]:
        """
        Attributes a text to FOF sub-strategies.
        Returns a list of tuples: (strategy_code, matched_keywords)
        """
        text_lower = text.lower()
        matched_strats = []
        
        for code, config in self.rules.items():
            matched_kws = [kw for kw in config["keywords"] if kw.lower() in text_lower]
            if matched_kws:
                matched_strats.append((code, matched_kws))
                
        return matched_strats

    def generate_report(self, scored_records: List[Dict[str, Any]]) -> str:
        """
        Generates a structured FOF Hypothesis Report (Markdown format) based on the processed records.
        """
        # Filter and group records by FOF strategy
        grouped_records: Dict[str, List[Dict[str, Any]]] = {code: [] for code in self.rules}
        
        for rec in scored_records:
            if 'fof_strategy' in rec and rec['fof_strategy']:
                for code in str(rec['fof_strategy']).split(','):
                    if code in grouped_records:
                        grouped_records[code].append(rec)

        report_lines = []
        report_lines.append("# 📊 阿尔法雷达：量化 FOF 策略归因与决策建议报告")
        report_lines.append(f"生成时间: {os.environ.get('EXECUTION_TIME', 'N/A')}\n")
        report_lines.append("---")

        for code, config in self.rules.items():
            records = grouped_records[code]
            if not records:
                continue
                
            report_lines.append(f"\n## ⚡ 【{config['name']}】 (代码: {code})")
            report_lines.append(f"> **定位**: {config['description']}")
            report_lines.append(f"\n### 📌 监测到 {len(records)} 条相关异动信号：")
            
            # Sort records by absolute score of FinNLP/Gemini
            sorted_recs = sorted(records, key=lambda x: abs(x.get('score_finnlp', 0)), reverse=True)
            
            for rec in sorted_recs[:5]:  # show top 5
                score = rec.get('score_finnlp', 0.0)
                sentiment = "🔴 利空" if score < -0.1 else ("🟢 利好" if score > 0.1 else "⚪ 中性")
                matched = rec.get('matched_keywords', [])
                report_lines.append(f"- **[{rec.get('source', '未知')}]** {rec.get('title')} ({sentiment} {score}, 匹配词: `{matched}`)")
                
            # Add strategy hypotheses
            report_lines.append("\n### 🔍 量化 FOF 投资假设与验证指令：")
            if code == "STYLE_FACTOR":
                report_lines.append("  * **【边际假设】**: 观察是否有微盘股流动性踩踏或大小盘估值分化加速。多头因子拥挤度增加预示着指增策略超额可能见顶。")
                report_lines.append("  * **【决策建议】**: 检查子基金的风格因子暴露，特别是小市值因子（Size）及动量因子。当前可能正处于量化选股策略超额收益“高拥挤、分化前夕”的敏感窗口。")
                report_lines.append("  * **【下一步验证】**: 调取各子管理人最新的周度超额收益（Alpha）数据，对比中证500/1000指增的超额回撤斜率，评估是否需要向大市值/红利指增策略调配资金。")
            elif code == "BETA_TIMING":
                report_lines.append("  * **【边际假设】**: 宏观流动性或者市场极端指数跌幅可能造成被动杠杆出清。")
                report_lines.append("  * **【决策建议】**: Beta 敞口暂时维持低水平或进行套期保值。密切关注科创50能否在“黄金坑”构建完成后企稳。")
                report_lines.append("  * **【下一步验证】**: 每日 15:00 提取两市两融余额及雪球敲入期权估算，研判是否有被动平仓盘带来的二次探底风险。")
            elif code == "HEDGE_COST":
                report_lines.append("  * **【边际假设】**: 股指期货基差贴水情况随全市场暴跌可能出现宽幅震荡。")
                report_lines.append("  * **【决策建议】**: 检查市场中性策略子基金的最新净值表现。基差若急剧贴水（深贴水）会增加中性策略开仓对冲成本，并可能导致中性策略面临短期基差收敛带来的浮亏。")
                report_lines.append("  * **【下一步验证】**: 计算中证500（IC）和中证1000（IM）当月与次月合约的年化贴水率变化，防范基差暴踩对中性策略造成双杀。")
            elif code == "HFT_REGULATION":
                report_lines.append("  * **【边际假设】**: 全市场成交额增减对高频T0环境有着决定性作用。如果出现极端地量或程序化新规，T0超额会受到压制。")
                report_lines.append("  * **【决策建议】**: 极高成交量通常伴随着剧烈的盘中波动和极大的市场换手率，这对 T0中性 策略和高频阿尔法策略是重大利好，T0 策略超额收益将显著飙升。")
                report_lines.append("  * **【下一步验证】**: 监测接下来 3 个交易日两市成交额是否能稳定维持在 1.5 万亿以上。如果是，可适度给 T0中性 管理人追加额度。")
            elif code == "CTA_TREND":
                report_lines.append("  * **【边际假设】**: 大宗商品库存异动或海外地缘冲突造成商品动量加剧。")
                report_lines.append("  * **【决策建议】**: 大宗商品基本面供需分化严重（有色偏多，镍偏空）。全球商品宽幅震荡利于“趋势跟踪”CTA策略。")
                report_lines.append("  * **【下一步验证】**: 追踪国内主要 CTA 管理人的动量因子收益表现，评估当前“期限结构（Roll Yield）”与“时序动量（TSM）”策略的共振强度，是否适合增加 CTA 策略的仓位权重。")
                
            report_lines.append("\n---")
            
        return "\n".join(report_lines)
