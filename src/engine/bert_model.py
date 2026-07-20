import os
import re
from typing import Tuple, Optional

# Ensure no proxy blockages during model downloading/loading
for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    if key in os.environ:
        del os.environ[key]

class BERTModel:
    def __init__(self, local_files_only: bool = True):
        self.local_files_only = local_files_only
        self.finbert_tokenizer = None
        self.finbert_model = None
        self.finbert_tone_tokenizer = None
        self.finbert_tone_model = None
        
        self.use_local_models = False
        self._init_models()

    def _init_models(self):
        """Attempts to load local FinBERT and FinBERT-Tone models."""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            print("[BERTModel] Loading ProsusAI/finbert (English)...")
            try:
                self.finbert_tokenizer = AutoTokenizer.from_pretrained(
                    "ProsusAI/finbert", 
                    local_files_only=self.local_files_only
                )
                self.finbert_model = AutoModelForSequenceClassification.from_pretrained(
                    "ProsusAI/finbert", 
                    local_files_only=self.local_files_only
                )
                self.finbert_model.eval()
                print("  Successfully loaded ProsusAI/finbert.")
            except Exception as e:
                print(f"  Warning: Failed to load ProsusAI/finbert (local_files_only={self.local_files_only}): {e}")

            print("[BERTModel] Loading yiyanghkust/finbert-tone (Chinese)...")
            try:
                self.finbert_tone_tokenizer = AutoTokenizer.from_pretrained(
                    "yiyanghkust/finbert-tone", 
                    local_files_only=self.local_files_only
                )
                self.finbert_tone_model = AutoModelForSequenceClassification.from_pretrained(
                    "yiyanghkust/finbert-tone", 
                    local_files_only=self.local_files_only
                )
                self.finbert_tone_model.eval()
                print("  Successfully loaded yiyanghkust/finbert-tone.")
            except Exception as e:
                print(f"  Warning: Failed to load yiyanghkust/finbert-tone (local_files_only={self.local_files_only}): {e}")
            
            if self.finbert_model or self.finbert_tone_model:
                self.use_local_models = True
        except ImportError:
            print("[BERTModel] Warning: torch or transformers is not installed in the Python environment.")
            self.use_local_models = False
        except Exception as e:
            print(f"[BERTModel] General initialization error: {e}")
            self.use_local_models = False

    def _is_chinese(self, text: str) -> bool:
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def score(self, text: str) -> Tuple[Optional[float], str]:
        """
        Calculates sentiment score using FinBERT models.
        Returns (score, channel_name). If models are not loaded, returns (None, 'Model-Unavailable').
        """
        if not self.use_local_models or not text or len(text.strip()) == 0:
            return None, "Model-Unavailable"

        is_zh = self._is_chinese(text)
        
        # 1. Run Chinese FinBERT-Tone
        if is_zh and self.finbert_tone_model:
            try:
                import torch
                inputs = self.finbert_tone_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = self.finbert_tone_model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze().tolist()
                
                # Labels: 0: Neutral, 1: Positive, 2: Negative
                neutral_p, positive_p, negative_p = probs[0], probs[1], probs[2]
                score = positive_p - negative_p
                return round(score, 4), "FinBERT-Tone"
            except Exception as e:
                print(f"[BERTModel] Chinese inference failed: {e}")
                return None, "Inference-Error"

        # 2. Run English FinBERT
        elif not is_zh and self.finbert_model:
            try:
                import torch
                inputs = self.finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = self.finbert_model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1).squeeze().tolist()
                
                # Labels: 0: Positive, 1: Negative, 2: Neutral
                positive_p, negative_p, neutral_p = probs[0], probs[1], probs[2]
                score = positive_p - negative_p
                return round(score, 4), "FinBERT-English"
            except Exception as e:
                print(f"[BERTModel] English inference failed: {e}")
                return None, "Inference-Error"

        return None, "Model-Mismatched"
