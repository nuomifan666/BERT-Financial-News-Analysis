"""
预测模块 - 加载模型进行情感预测
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'model', 'saved')
MAX_SEQ_LEN = 128


class SentimentPredictor:
    """情感分析预测器"""

    def __init__(self, model_dir=None):
        """初始化预测器"""
        if model_dir is None:
            model_dir = MODEL_DIR

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if os.path.exists(model_dir):
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
            self.model.to(self.device)
            self.model.eval()
            self.loaded = True
            print(f"✅ 模型加载成功 | 设备: {self.device}")
            if torch.cuda.is_available():
                print(f"   GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.loaded = False
            print(f"⚠️  模型未找到: {model_dir}")
            print("   请先运行 model/train.py 训练模型")

    def predict(self, texts):
        """预测单条或多条文本"""
        if not self.loaded:
            return self._mock_predict(texts)

        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False

        results = []

        with torch.no_grad():
            for text in texts:
                encoding = self.tokenizer(
                    str(text),
                    max_length=MAX_SEQ_LEN,
                    padding='max_length',
                    truncation=True,
                    return_tensors='pt'
                )
                encoding = {k: v.to(self.device) for k, v in encoding.items()}

                outputs = self.model(**encoding)
                probs = torch.softmax(outputs.logits, dim=1)
                pred = torch.argmax(probs, dim=1).item()
                confidence = probs[0, pred].item()

                result = {
                    'text': str(text),
                    'sentiment': 'positive' if pred == 1 else 'negative',
                    'sentiment_zh': '📈 积极' if pred == 1 else '📉 消极',
                    'label': int(pred),
                    'confidence': round(confidence, 4),
                    'prob_negative': round(probs[0, 0].item(), 4),
                    'prob_positive': round(probs[0, 1].item(), 4),
                }

                # 买卖信号
                if pred == 1 and confidence > 0.8:
                    result['signal'] = 'strong_buy'
                    result['signal_zh'] = '🟢 强烈看多'
                elif pred == 1 and confidence > 0.6:
                    result['signal'] = 'buy'
                    result['signal_zh'] = '🟡 偏多'
                elif pred == 0 and confidence > 0.8:
                    result['signal'] = 'strong_sell'
                    result['signal_zh'] = '🔴 强烈看空'
                elif pred == 0 and confidence > 0.6:
                    result['signal'] = 'sell'
                    result['signal_zh'] = '🟠 偏空'
                else:
                    result['signal'] = 'neutral'
                    result['signal_zh'] = '⚪ 中性'

                results.append(result)

        if single_input:
            return results[0]
        return results

    def predict_batch(self, texts, batch_size=32):
        """批量预测"""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self.predict(batch))
        return results

    def _mock_predict(self, texts):
        """无模型时的模拟预测"""
        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False

        results = []
        positive_keywords = ['增长', '上涨', '盈利', '合作', '签约', '中标', '投产',
                            '获批', '增持', '回购', '分红', '突破', '创新', '订单']
        negative_keywords = ['下跌', '亏损', '处罚', '诉讼', '减持', '退市', '违约',
                            '立案', '冻结', '预警', '暴跌', '暴雷', '风险', '停产']

        for text in texts:
            pos_count = sum(1 for w in positive_keywords if w in str(text))
            neg_count = sum(1 for w in negative_keywords if w in str(text))

            if pos_count > neg_count:
                pred, conf = 1, 0.75
            elif neg_count > pos_count:
                pred, conf = 0, 0.75
            else:
                pred, conf = 1, 0.55

            results.append({
                'text': str(text),
                'sentiment': 'positive' if pred == 1 else 'negative',
                'sentiment_zh': '📈 积极' if pred == 1 else '📉 消极',
                'label': int(pred),
                'confidence': conf,
                'prob_negative': round(1 - conf, 4) if pred == 1 else round(conf, 4),
                'prob_positive': round(conf, 4) if pred == 1 else round(1 - conf, 4),
                'signal': 'buy' if pred == 1 else 'sell',
                'signal_zh': '🟡 偏多(模拟)' if pred == 1 else '🟠 偏空(模拟)',
                '_mock': True,
            })

        if single_input:
            return results[0]
        return results


# 全局预测器实例
predictor = SentimentPredictor()


def get_predictor():
    """获取全局预测器"""
    return predictor
