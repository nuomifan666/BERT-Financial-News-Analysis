"""
BERT 金融新闻情感分析 - 模型训练脚本
使用 HuggingFace Transformers 库，支持 GPU 训练
"""

import os
import json
import time
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
from transformers.trainer_callback import EarlyStoppingCallback
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    classification_report, confusion_matrix, roc_auc_score, roc_curve
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm


# ==================== 配置 ====================
class Config:
    # 路径
    data_path = "train_test_data.xlsx"
    model_save_dir = "model/saved"
    result_dir = "model/results"

    # 模型参数
    pretrained_model = "bert-base-chinese"
    num_labels = 2
    max_seq_len = 128
    batch_size = 32
    learning_rate = 2e-5
    num_epochs = 10
    warmup_ratio = 0.1
    weight_decay = 0.01

    # 训练参数
    train_ratio = 0.7
    val_ratio = 0.15
    test_ratio = 0.15
    early_stopping_patience = 3
    eval_steps = 50
    save_steps = 100

    # 设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


cfg = Config()


# ==================== 数据集 ====================
class FinancialNewsDataset(Dataset):
    """金融新闻数据集"""
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = int(self.labels[idx])

        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


# ==================== 评估函数 ====================
def compute_metrics(pred):
    """计算评估指标"""
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    probs = pred.predictions

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average='weighted', zero_division=0
    )
    acc = accuracy_score(labels, preds)

    # 尝试计算AUC（仅二分类）
    try:
        auc = roc_auc_score(labels, probs[:, 1])
    except:
        auc = 0.0

    return {
        'accuracy': acc,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'auc': auc
    }


# ==================== 训练主函数 ====================
def load_and_split_data():
    """加载并切分数据"""
    print("=" * 60)
    print("📦 加载数据集...")
    print("=" * 60)

    # 读取 train 和 test sheet
    io = pd.io.excel.ExcelFile(cfg.data_path)
    train_raw = pd.read_excel(io, sheet_name='train')
    test_raw = pd.read_excel(io, sheet_name='test')
    io.close()

    # 合并所有数据
    df = pd.concat([train_raw, test_raw], ignore_index=True)

    texts = df['comment'].tolist()
    labels = df['sentiment'].tolist()

    print(f"   总样本: {len(texts)}")
    print(f"   正面(1): {sum(labels)} ({sum(labels)/len(labels)*100:.1f}%)")
    print(f"   负面(0): {len(labels)-sum(labels)} ({(len(labels)-sum(labels))/len(labels)*100:.1f}%)")

    # 分层划分
    X_temp, X_test, y_temp, y_test = train_test_split(
        texts, labels, test_size=cfg.test_ratio,
        stratify=labels, random_state=42
    )
    val_ratio_adjusted = cfg.val_ratio / (cfg.train_ratio + cfg.val_ratio)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_ratio_adjusted,
        stratify=y_temp, random_state=42
    )

    print(f"\n   训练集: {len(X_train)}")
    print(f"   验证集: {len(X_val)}")
    print(f"   测试集: {len(X_test)}")

    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def train_model():
    """主训练流程"""
    print(f"\n🚀 设备: {cfg.device}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    # 创建输出目录
    os.makedirs(cfg.model_save_dir, exist_ok=True)
    os.makedirs(cfg.result_dir, exist_ok=True)

    # 加载数据
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_and_split_data()

    # 加载 tokenizer
    print("\n" + "=" * 60)
    print("🔧 加载 Tokenizer & 模型...")
    print("=" * 60)
    tokenizer = AutoTokenizer.from_pretrained(cfg.pretrained_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.pretrained_model, num_labels=cfg.num_labels
    )

    # 创建数据集
    train_dataset = FinancialNewsDataset(X_train, y_train, tokenizer, cfg.max_seq_len)
    val_dataset = FinancialNewsDataset(X_val, y_val, tokenizer, cfg.max_seq_len)
    test_dataset = FinancialNewsDataset(X_test, y_test, tokenizer, cfg.max_seq_len)

    # 训练参数
    training_args = TrainingArguments(
        output_dir=cfg.model_save_dir,
        num_train_epochs=cfg.num_epochs,
        per_device_train_batch_size=cfg.batch_size,
        per_device_eval_batch_size=cfg.batch_size * 2,
        learning_rate=cfg.learning_rate,
        warmup_ratio=cfg.warmup_ratio,
        weight_decay=cfg.weight_decay,
        logging_dir=os.path.join(cfg.result_dir, 'logs'),
        logging_steps=cfg.eval_steps,
        eval_strategy='steps',
        eval_steps=cfg.eval_steps,
        save_steps=cfg.save_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model='eval_f1',
        greater_is_better=True,
        fp16=torch.cuda.is_available(),
        dataloader_num_workers=0,
        report_to='none',
        seed=42,
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=cfg.early_stopping_patience)],
    )

    # 训练
    print("\n" + "=" * 60)
    print("🎯 开始训练...")
    print("=" * 60)
    start_time = time.time()
    train_result = trainer.train()
    train_time = time.time() - start_time
    print(f"\n⏱️  训练耗时: {train_time/60:.1f} 分钟")

    # 保存模型
    print("\n💾 保存最佳模型...")
    trainer.save_model(cfg.model_save_dir)
    tokenizer.save_pretrained(cfg.model_save_dir)
    print(f"   模型已保存到: {cfg.model_save_dir}")

    # ==================== 测试集评估 ====================
    print("\n" + "=" * 60)
    print("📊 测试集评估...")
    print("=" * 60)

    test_result = trainer.evaluate(test_dataset)
    print(f"\n   准确率:  {test_result['eval_accuracy']:.4f}")
    print(f"   精确率:  {test_result['eval_precision']:.4f}")
    print(f"   召回率:  {test_result['eval_recall']:.4f}")
    print(f"   F1分数:  {test_result['eval_f1']:.4f}")
    print(f"   AUC:     {test_result['eval_auc']:.4f}")

    # 详细分类报告
    predictions = trainer.predict(test_dataset)
    y_pred = predictions.predictions.argmax(-1)
    y_prob = predictions.predictions
    print("\n" + classification_report(y_test, y_pred, target_names=['消极', '积极'], digits=4))

    # ==================== 保存训练历史和可视化 ====================
    print("\n📈 生成可视化图表...")
    save_all_visualizations(trainer, train_result, y_test, y_pred, y_prob)

    # 保存元数据
    metadata = {
        'model_name': cfg.pretrained_model,
        'num_labels': cfg.num_labels,
        'train_samples': len(X_train),
        'val_samples': len(X_val),
        'test_samples': len(X_test),
        'test_accuracy': float(test_result['eval_accuracy']),
        'test_precision': float(test_result['eval_precision']),
        'test_recall': float(test_result['eval_recall']),
        'test_f1': float(test_result['eval_f1']),
        'test_auc': float(test_result['eval_auc']),
        'train_time_minutes': round(train_time / 60, 1),
    }
    with open(os.path.join(cfg.result_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n✅ 训练完成！")
    return trainer, model, tokenizer


def save_all_visualizations(trainer, train_result, y_test, y_pred, y_prob):
    """生成所有可视化图表"""

    # ---- 1. 训练曲线 ----
    log_history = trainer.state.log_history

    # 提取训练和验证的 metrics
    train_steps, train_losses = [], []
    eval_steps, eval_losses, eval_accs, eval_f1s = [], [], [], []

    for entry in log_history:
        if 'loss' in entry and 'eval_loss' not in entry:
            train_steps.append(entry['step'])
            train_losses.append(entry['loss'])
        if 'eval_loss' in entry:
            eval_steps.append(entry['step'])
            eval_losses.append(entry['eval_loss'])
            eval_accs.append(entry.get('eval_accuracy', 0))
            eval_f1s.append(entry.get('eval_f1', 0))

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Loss
    axes[0].plot(train_steps, train_losses, 'b-', label='训练Loss', alpha=0.7)
    axes[0].plot(eval_steps, eval_losses, 'r-o', label='验证Loss', markersize=4)
    axes[0].set_title('训练 & 验证 Loss', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Steps')
    axes[0].set_ylabel('Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Accuracy
    axes[1].plot(eval_steps, eval_accs, 'g-o', markersize=4)
    axes[1].set_title('验证准确率', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Steps')
    axes[1].set_ylabel('Accuracy')
    axes[1].grid(True, alpha=0.3)

    # F1
    axes[2].plot(eval_steps, eval_f1s, 'purple', marker='o', markersize=4)
    axes[2].set_title('验证 F1 Score', fontsize=14, fontweight='bold')
    axes[2].set_xlabel('Steps')
    axes[2].set_ylabel('F1')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(cfg.result_dir, 'training_curves.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # ---- 2. 混淆矩阵 ----
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['消极', '积极'],
                yticklabels=['消极', '积极'],
                annot_kws={'fontsize': 20})
    ax.set_title('混淆矩阵', fontsize=16, fontweight='bold')
    ax.set_xlabel('预测标签', fontsize=12)
    ax.set_ylabel('真实标签', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(cfg.result_dir, 'confusion_matrix.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # ---- 3. ROC 曲线 ----
    try:
        fpr, tpr, _ = roc_curve(y_test, y_prob[:, 1])
        auc = roc_auc_score(y_test, y_prob[:, 1])

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC = {auc:.4f})')
        ax.plot([0, 1], [0, 1], 'r--', linewidth=1, label='随机分类器')
        ax.fill_between(fpr, tpr, alpha=0.3)
        ax.set_title('ROC 曲线', fontsize=16, fontweight='bold')
        ax.set_xlabel('False Positive Rate', fontsize=12)
        ax.set_ylabel('True Positive Rate', fontsize=12)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(cfg.result_dir, 'roc_curve.png'), dpi=150, bbox_inches='tight')
        plt.close()
    except Exception as e:
        print(f"   ROC曲线生成失败: {e}")

    # ---- 4. 预测概率分布 ----
    fig, ax = plt.subplots(figsize=(10, 5))
    pos_probs = y_prob[y_test == 1, 1]
    neg_probs = y_prob[y_test == 0, 1]
    ax.hist(pos_probs, bins=30, alpha=0.6, label='正面新闻', color='green', edgecolor='black')
    ax.hist(neg_probs, bins=30, alpha=0.6, label='负面新闻', color='red', edgecolor='black')
    ax.axvline(x=0.5, color='black', linestyle='--', linewidth=1, label='决策边界')
    ax.set_title('预测概率分布', fontsize=14, fontweight='bold')
    ax.set_xlabel('预测为正面的概率')
    ax.set_ylabel('频数')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(cfg.result_dir, 'probability_distribution.png'), dpi=150, bbox_inches='tight')
    plt.close()

    print(f"   图表已保存到: {cfg.result_dir}/")


def load_trained_model(model_dir=None):
    """加载已训练的模型和tokenizer"""
    if model_dir is None:
        model_dir = cfg.model_save_dir

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.to(cfg.device)
    model.eval()
    return model, tokenizer


def predict(texts, model=None, tokenizer=None):
    """预测函数"""
    if model is None or tokenizer is None:
        model, tokenizer = load_trained_model()

    if isinstance(texts, str):
        texts = [texts]

    model.eval()
    results = []

    with torch.no_grad():
        for text in texts:
            encoding = tokenizer(
                text, max_length=cfg.max_seq_len,
                padding='max_length', truncation=True,
                return_tensors='pt'
            )
            encoding = {k: v.to(cfg.device) for k, v in encoding.items()}

            outputs = model(**encoding)
            probs = torch.softmax(outputs.logits, dim=1)
            pred = torch.argmax(probs, dim=1).item()
            confidence = probs[0, pred].item()

            results.append({
                'text': text,
                'sentiment': 'positive' if pred == 1 else 'negative',
                'sentiment_zh': '📈 积极' if pred == 1 else '📉 消极',
                'confidence': round(confidence, 4),
                'probabilities': {
                    'negative': round(probs[0, 0].item(), 4),
                    'positive': round(probs[0, 1].item(), 4)
                }
            })

    if len(results) == 1:
        return results[0]
    return results


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 BERT 金融新闻情感分析 - 模型训练")
    print(f"📅 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    trainer, model, tokenizer = train_model()

    # 简单测试
    print("\n" + "=" * 60)
    print("🧪 模型预测测试...")
    print("=" * 60)
    test_texts = [
        "公司预计全年净利润同比增长超过50%",
        "公司收到证监会立案调查通知书",
        "海能达与非洲某国公共安全客户签订千万美元项目合同",
        "公司控股股东拟减持不超过3%的股份",
    ]
    for text in test_texts:
        result = predict(text, model, tokenizer)
        print(f"   {result['sentiment_zh']} | {text[:40]}... (置信度: {result['confidence']:.2%})")
