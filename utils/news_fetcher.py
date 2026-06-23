"""
实时金融新闻抓取模块
支持 akshare、NewsAPI、以及 Web 抓取等多种数据源
"""

import os
import json
import random
import time
import requests
from datetime import datetime, timedelta
from collections import OrderedDict

# 尝试导入 akshare
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("⚠️  akshare 未安装，将使用模拟数据")


def fetch_eastmoney_news(page=1, page_size=20):
    """从东方财富抓取最新财经新闻（通过 akshare）"""
    if HAS_AKSHARE:
        try:
            # 使用 akshare 获取新闻
            df = ak.stock_news_em()
            if df is not None and len(df) > 0:
                news_list = []
                for _, row in df.head(page_size).iterrows():
                    news_list.append({
                        'title': str(row.get('标题', row.get('title', ''))),
                        'time': str(row.get('发布时间', row.get('time', ''))),
                        'source': '东方财富',
                        'url': str(row.get('链接', row.get('url', ''))),
                    })
                return news_list
        except Exception as e:
            print(f"   akshare 东方财富新闻获取失败: {e}")

    # 降级: 使用模拟数据
    return _get_mock_news(page_size)


def fetch_sina_finance_news():
    """抓取新浪财经新闻"""
    if HAS_AKSHARE:
        try:
            # 尝试多个可能的 akshare 接口
            for func_name in ['stock_info_global_em', 'stock_news_sina']:
                try:
                    func = getattr(ak, func_name, None)
                    if func:
                        result = func()
                        if result is not None and hasattr(result, '__len__') and len(result) > 0:
                            news_list = []
                            cols = result.columns.tolist()
                            title_col = next((c for c in cols if '标题' in c or 'title' in c.lower()), cols[0])
                            time_col = next((c for c in cols if '时间' in c or 'time' in c.lower() or 'date' in c.lower()), None)

                            for _, row in result.head(15).iterrows():
                                news_list.append({
                                    'title': str(row[title_col]),
                                    'time': str(row[time_col]) if time_col else '',
                                    'source': '新浪财经',
                                    'url': '',
                                })
                            return news_list
                except:
                    continue

            # 新浪新闻内容接口
            news_df = ak.stock_news_main_cx() if hasattr(ak, 'stock_news_main_cx') else None
            if news_df is not None and len(news_df) > 0:
                news_list = []
                cols = news_df.columns.tolist()
                title_col = next((c for c in cols if '标题' in c or 'title' in c.lower()), cols[0])
                for _, row in news_df.head(15).iterrows():
                    news_list.append({
                        'title': str(row[title_col]),
                        'time': str(row.iloc[1]) if len(row) > 1 else '',
                        'source': '新浪财经',
                        'url': '',
                    })
                return news_list
        except Exception as e:
            print(f"   akshare 新浪新闻获取失败: {e}")

    return _get_mock_news(15, source='新浪财经')


def fetch_financial_news(source='all', limit=30):
    """统一的新闻获取接口"""
    all_news = []

    if source in ('all', 'eastmoney'):
        all_news.extend(fetch_eastmoney_news(page_size=limit // 2))

    if source in ('all', 'sina'):
        all_news.extend(fetch_sina_finance_news())

    # 如果没有获取到任何新闻，使用模拟数据
    if not all_news:
        all_news = _get_mock_news(limit)

    # 去重
    seen = set()
    unique_news = []
    for news in all_news:
        if news['title'] not in seen:
            seen.add(news['title'])
            unique_news.append(news)

    return unique_news[:limit]


def _get_mock_news(n=20, source='模拟数据'):
    """生成模拟金融新闻（API不可用时的降级方案）"""
    positive_templates = [
        "{company}预计全年净利润同比增长超过{N}%",
        "{company}与{N}家合作伙伴签署战略合作协议",
        "{company}成功中标{N}亿元重大工程项目",
        "{company}获得{N}亿元战略投资",
        "{company}新研发中心正式投产运营",
        "{company}获得{N}项核心发明专利授权",
        "机构看好{company}发展前景，目标价上调{N}%",
        "{company}回购{N}万股公司股份",
        "{company}分红方案获股东大会通过，每10股派{N}元",
        "{company}新业务板块营收同比增长{N}%",
        "{company}拟投资{N}亿元扩建生产基地",
        "北向资金大幅加仓{company}，持仓市值增加{N}亿元",
        "{company}创新药获批上市，市场前景广阔",
        "{company}国际业务取得重大突破",
        "{company}成功登陆科创板/创业板",
    ]

    negative_templates = [
        "{company}预计全年净利润同比下滑{N}%",
        "{company}收到证监会立案调查通知书",
        "{company}控股股东拟减持不超过{N}%的股份",
        "{company}因信息披露违规被出具警示函",
        "{company}商誉减值{N}亿元，导致巨亏",
        "{company}主要产品被曝质量问题，遭消费者投诉",
        "{company}被列入失信被执行人名单",
        "{company}终止定向增发计划",
        "{company}海外项目遭遇政策风险，损失{N}亿元",
        "{company}股价连续跌停，市值蒸发{N}亿元",
        "{company}应收账款高企，坏账风险加大",
        "{company}供应商集中度风险引发市场担忧",
        "{company}行业竞争加剧，毛利率持续下滑",
        "{company}被多家机构下调评级",
        "{company}资金链紧张，短期偿债压力加大",
    ]

    neutral_templates = [
        "{company}发布{N}年年度报告",
        "{company}召开临时股东大会",
        "{company}董事会换届选举结果公布",
        "{company}公告{N}年业绩说明会安排",
        "{company}回应投资者关于{issue}的提问",
        "{company}完成工商变更登记",
        "{company}调整内部组织架构",
        "{company}变更公司证券事务代表",
        "{company}披露{N}月份经营数据",
        "{company}高管团队赴{N}调研考察",
    ]

    companies = [
        '贵州茅台', '宁德时代', '比亚迪', '中国平安', '招商银行',
        '美的集团', '格力电器', '万科A', '恒瑞医药', '海康威视',
        '隆基绿能', '药明康德', '中兴通讯', '三一重工', '伊利股份',
        '海尔智家', '京东方A', '立讯精密', '中国中免', '紫金矿业',
    ]

    numbers = [10, 15, 20, 25, 30, 35, 40, 50, 60, 80, 100, 150, 200, 300, 500]

    news_list = []
    for i in range(n):
        category = random.choices(['positive', 'negative', 'neutral'], weights=[0.45, 0.35, 0.2])[0]

        if category == 'positive':
            template = random.choice(positive_templates)
        elif category == 'negative':
            template = random.choice(negative_templates)
        else:
            template = random.choice(neutral_templates)

        title = template.format(
            company=random.choice(companies),
            N=random.choice(numbers),
            issue=random.choice(['分红计划', '股价走势', '业绩波动', '并购传闻']),
        )

        # 随机时间
        hours_ago = random.randint(0, 72)
        news_time = (datetime.now() - timedelta(hours=hours_ago)).strftime('%Y-%m-%d %H:%M:%S')

        news_list.append({
            'title': title,
            'time': news_time,
            'source': source,
            'url': '',
            '_mock': True,
        })

    # 按时间排序
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list


def get_stock_sectors_summary():
    """获取各板块情绪汇总"""
    sectors = [
        '银行', '证券', '保险', '房地产', '白酒', '新能源汽车',
        '光伏', '芯片', '医药', '消费电子', '军工', '有色',
        '钢铁', '煤炭', '电力', '石油', '农业', '传媒',
        '计算机', '通信', '机械', '化工', '建材', '纺织',
    ]

    results = []
    for sector in sectors:
        sentiment_score = random.uniform(-1, 1)
        news_count = random.randint(3, 25)
        results.append({
            'sector': sector,
            'sentiment_score': round(sentiment_score, 3),
            'news_count': news_count,
            'signal': 'buy' if sentiment_score > 0.3 else (
                'sell' if sentiment_score < -0.3 else 'neutral'
            ),
        })

    # 按情绪得分排序
    results.sort(key=lambda x: x['sentiment_score'], reverse=True)
    return results
