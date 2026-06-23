"""
数据加载工具 - 加载和处理金融新闻数据
"""

import os
import json
import random
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_local_data():
    """加载本地数据集"""
    filepath = os.path.join(BASE_DIR, 'train_test_data.xlsx')

    if not os.path.exists(filepath):
        return None, None

    io = pd.io.excel.ExcelFile(filepath)
    train_raw = pd.read_excel(io, sheet_name='train')
    test_raw = pd.read_excel(io, sheet_name='test')
    io.close()

    df = pd.concat([train_raw, test_raw], ignore_index=True)

    # 只保留需要的列
    if 'comment' in df.columns and 'sentiment' in df.columns:
        df = df[['comment', 'sentiment']]

    return df, df['comment'].tolist()


def get_data_statistics():
    """获取数据集统计信息"""
    df, _ = load_local_data()
    if df is None:
        return {}

    total = len(df)
    positive = int(df['sentiment'].sum())
    negative = total - positive

    # 文本长度分布
    lengths = df['comment'].str.len()
    length_bins = [0, 20, 40, 60, 80, 100, 150, 200, 500]
    length_labels = ['0-20', '21-40', '41-60', '61-80', '81-100', '101-150', '151-200', '200+']
    length_dist = pd.cut(lengths, bins=length_bins, labels=length_labels).value_counts().sort_index()

    return {
        'total': total,
        'positive': positive,
        'negative': negative,
        'positive_ratio': round(positive / total * 100, 1),
        'negative_ratio': round(negative / total * 100, 1),
        'avg_length': round(float(lengths.mean()), 1),
        'max_length': int(lengths.max()),
        'min_length': int(lengths.min()),
        'length_distribution': {
            'labels': length_dist.index.tolist(),
            'values': length_dist.values.tolist(),
        },
    }


def get_sample_data(n=20):
    """获取随机样本数据用于展示"""
    df, _ = load_local_data()
    if df is None:
        return []

    samples = df.sample(min(n, len(df))).to_dict('records')
    return samples


def get_model_metadata():
    """获取模型训练元数据"""
    metadata_path = os.path.join(BASE_DIR, 'model', 'results', 'metadata.json')
    if not os.path.exists(metadata_path):
        return {}

    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_training_history():
    """获取训练历史数据"""
    result_path = os.path.join(BASE_DIR, 'result.txt')
    if not os.path.exists(result_path):
        return []

    with open(result_path, 'r') as f:
        data = f.readlines()

    accuracy, macro_f1, weighted_f1 = [], [], []
    macro_precision, macro_recall = [], []
    weighted_precision, weighted_recall = [], []

    for line in data:
        if 'accuracy' in line:
            accuracy.append(float(line.split()[1]))
        elif 'macro avg' in line:
            parts = line.split()
            macro_precision.append(float(parts[2]))
            macro_recall.append(float(parts[3]))
            macro_f1.append(float(parts[4]))
        elif 'weighted avg' in line:
            parts = line.split()
            weighted_precision.append(float(parts[2]))
            weighted_recall.append(float(parts[3]))
            weighted_f1.append(float(parts[4]))

    history = []
    for i in range(len(accuracy)):
        history.append({
            'iteration': i + 1,
            'accuracy': accuracy[i],
            'macro_precision': macro_precision[i] if i < len(macro_precision) else 0,
            'macro_recall': macro_recall[i] if i < len(macro_recall) else 0,
            'macro_f1': macro_f1[i] if i < len(macro_f1) else 0,
            'weighted_precision': weighted_precision[i] if i < len(weighted_precision) else 0,
            'weighted_recall': weighted_recall[i] if i < len(weighted_recall) else 0,
            'weighted_f1': weighted_f1[i] if i < len(weighted_f1) else 0,
        })

    return history
