"""
Flask Web 应用 - BERT 金融新闻情感分析系统
提供 RESTful API 和 Web 页面
"""

import os
import sys
import json
import random
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file

# 添加项目根目录到 path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from model.predict import SentimentPredictor, get_predictor
from utils.data_loader import (
    load_local_data, get_data_statistics, get_sample_data,
    get_training_history, get_model_metadata
)
from utils.visualization import (
    generate_wordcloud_data, generate_confusion_matrix_data,
    generate_training_history_data, generate_roc_data,
    generate_correlation_heatmap, generate_confidence_distribution,
)
from utils.news_fetcher import (
    fetch_sample_news, fetch_real_news, get_stock_sectors_summary,
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# 初始化预测器
predictor = None


def init_predictor():
    """初始化全局预测器"""
    global predictor
    predictor = SentimentPredictor()
    return predictor


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


# ==================== API: 预测 ====================

@app.route('/api/predict', methods=['POST'])
def api_predict():
    """单条/多条文本预测"""
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': '请提供text字段'}), 400

    text = data['text']
    if not text or not text.strip():
        return jsonify({'error': '文本不能为空'}), 400

    result = predictor.predict(text.strip())
    return jsonify(result)


@app.route('/api/predict_batch', methods=['POST'])
def api_predict_batch():
    """批量预测"""
    data = request.get_json()
    if not data or 'texts' not in data:
        return jsonify({'error': '请提供texts字段（字符串列表）'}), 400

    texts = data['texts']
    if not isinstance(texts, list) or len(texts) == 0:
        return jsonify({'error': 'texts必须是非空列表'}), 400

    results = predictor.predict_batch(texts)
    return jsonify({
        'total': len(results),
        'results': results,
        'summary': {
            'positive': sum(1 for r in results if r['sentiment'] == 'positive'),
            'negative': sum(1 for r in results if r['sentiment'] == 'negative'),
        }
    })


# ==================== API: 数据统计 ====================

@app.route('/api/data/statistics')
def api_data_statistics():
    """获取数据集统计信息"""
    stats = get_data_statistics()
    return jsonify(stats)


@app.route('/api/data/samples')
def api_data_samples():
    """获取随机样本"""
    n = request.args.get('n', 20, type=int)
    samples = get_sample_data(n)
    return jsonify(samples)


@app.route('/api/data/full')
def api_data_full():
    """获取完整数据集（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    df, _ = load_local_data()
    if df is None:
        return jsonify({'error': '数据未找到'}), 404

    total = len(df)
    start = (page - 1) * per_page
    end = start + per_page
    page_data = df.iloc[start:end].to_dict('records')

    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'data': page_data,
    })


# ==================== API: 可视化数据 ====================

@app.route('/api/visualization/training_history')
def api_training_history():
    """获取训练历史数据"""
    data = generate_training_history_data()
    return jsonify(data)


@app.route('/api/visualization/wordcloud')
def api_wordcloud():
    """获取词云数据"""
    data = generate_wordcloud_data()
    return jsonify(data)


@app.route('/api/visualization/confusion_matrix')
def api_confusion_matrix():
    """获取混淆矩阵数据"""
    data = generate_confusion_matrix_data()
    return jsonify(data)


@app.route('/api/visualization/roc')
def api_roc():
    """获取ROC曲线数据"""
    data = generate_roc_data()
    return jsonify(data)


@app.route('/api/visualization/correlation')
def api_correlation():
    """获取相关性热力图数据"""
    data = generate_correlation_heatmap()
    return jsonify(data)


@app.route('/api/visualization/confidence')
def api_confidence():
    """获取置信度分布数据"""
    data = generate_confidence_distribution()
    return jsonify(data)


@app.route('/api/model/metadata')
def api_model_metadata():
    """获取模型元数据"""
    metadata = get_model_metadata()

    # 补充预测器状态
    metadata['model_loaded'] = predictor.loaded if predictor else False
    metadata['device'] = str(predictor.device) if predictor else 'unknown'

    return jsonify(metadata)


# ==================== API: 新闻 ====================

def _analyze_news(news_list):
    """对新闻列表进行情感分析，返回分析后的新闻列表和汇总数据"""
    titles = [n['title'] for n in news_list]
    results = predictor.predict_batch(titles)

    for i, news in enumerate(news_list):
        if i < len(results):
            news['sentiment'] = results[i]['sentiment']
            news['sentiment_zh'] = results[i]['sentiment_zh']
            news['confidence'] = results[i]['confidence']
            news['signal'] = results[i]['signal']
            news['signal_zh'] = results[i]['signal_zh']
            news['prob_positive'] = results[i]['prob_positive']
            news['prob_negative'] = results[i]['prob_negative']
        else:
            news['sentiment'] = 'neutral'
            news['sentiment_zh'] = '中性'
            news['confidence'] = 0.5
            news['signal'] = 'neutral'
            news['signal_zh'] = '中性'

    positive_count = sum(1 for n in news_list if n.get('sentiment') == 'positive')
    negative_count = sum(1 for n in news_list if n.get('sentiment') == 'negative')

    if len(news_list) > 0:
        sentiment_ratio = (positive_count - negative_count) / len(news_list)
        if sentiment_ratio > 0.2:
            market_signal, market_signal_en = '看多', 'bullish'
        elif sentiment_ratio < -0.2:
            market_signal, market_signal_en = '看空', 'bearish'
        else:
            market_signal, market_signal_en = '中性', 'neutral'
    else:
        sentiment_ratio = 0
        market_signal, market_signal_en = '暂无数据', 'none'

    return news_list, {
        'total': len(news_list),
        'positive_count': positive_count,
        'negative_count': negative_count,
        'sentiment_ratio': round(sentiment_ratio, 3),
        'market_signal': market_signal,
        'market_signal_en': market_signal_en,
    }


@app.route('/api/news/sample')
def api_news_sample():
    """获取样例新闻（基于本地数据集）"""
    limit = request.args.get('limit', 30, type=int)
    news_list = fetch_sample_news(limit=limit)
    news_list, summary = _analyze_news(news_list)
    sectors = get_stock_sectors_summary(news_list)

    return jsonify({
        'source': 'sample',
        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'news': news_list,
        'sectors': sectors,
        **summary,
    })


@app.route('/api/news/realtime')
def api_news_realtime():
    """获取真实实时金融新闻（新浪财经）"""
    limit = request.args.get('limit', 30, type=int)
    news_list = fetch_real_news(limit=limit)
    news_list, summary = _analyze_news(news_list)
    sectors = get_stock_sectors_summary(news_list)

    return jsonify({
        'source': 'realtime',
        'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'news': news_list,
        'sectors': sectors,
        **summary,
    })


# ==================== API: 批量文件分析 ====================

@app.route('/api/upload_analyze', methods=['POST'])
def api_upload_analyze():
    """上传文件进行批量情感分析"""
    if 'file' not in request.files:
        return jsonify({'error': '未找到上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    try:
        # 根据文件类型读取
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': '请上传 CSV 或 Excel 文件'}), 400

        # 查找文本列
        text_col = None
        for col in df.columns:
            if any(kw in str(col).lower() for kw in ['text', 'title', 'comment', '新闻', '标题', '内容', '文本']):
                text_col = col
                break

        if text_col is None:
            text_col = df.columns[0]  # 默认第一列

        texts = df[text_col].astype(str).tolist()
        results = predictor.predict_batch(texts)

        # 将结果添加到 DataFrame
        df['情感'] = [r['sentiment_zh'] for r in results]
        df['置信度'] = [r['confidence'] for r in results]
        df['信号'] = [r['signal_zh'] for r in results]

        # 保存结果
        output_filename = f'analysis_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        output_path = os.path.join(BASE_DIR, 'static', 'downloads', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_excel(output_path, index=False)

        return jsonify({
            'total': len(results),
            'positive': sum(1 for r in results if r['sentiment'] == 'positive'),
            'negative': sum(1 for r in results if r['sentiment'] == 'negative'),
            'download_url': f'/static/downloads/{output_filename}',
            'preview': results[:10],
        })

    except Exception as e:
        return jsonify({'error': f'文件处理失败: {str(e)}'}), 500


# ==================== 启动 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 BERT 金融新闻情感分析系统")
    print("=" * 60)

    # 初始化预测器
    init_predictor()

    print("\n🌐 启动 Web 服务...")
    print("   本地访问: http://127.0.0.1:5000")
    print("   局域网访问: http://<your-ip>:5000")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)
