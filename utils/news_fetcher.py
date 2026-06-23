"""
金融新闻抓取模块
- 样例数据: 基于本地数据集生成
- 实时新闻: 从新浪财经实时抓取
"""

import random
import requests
from datetime import datetime, timedelta


# ==================== 实时新闻抓取 ====================

def fetch_sina_realtime_news(limit=30):
    """从新浪财经实时抓取最新金融新闻"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = f'https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num={min(limit, 50)}&page=1'
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()
        if 'result' not in data or 'data' not in data['result']:
            return None

        items = data['result']['data']
        news_list = []
        for item in items:
            title = item.get('title', '').strip()
            if not title:
                continue
            # 转换时间戳
            ts = item.get('ctime', '')
            try:
                t = datetime.fromtimestamp(int(ts))
                time_str = t.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = str(ts)

            news_list.append({
                'title': title,
                'time': time_str,
                'source': '新浪财经',
                'url': item.get('url', ''),
                '_real': True,
            })

        return news_list[:limit]

    except Exception as e:
        print(f"新浪财经抓取失败: {e}")
        return None


def fetch_real_news(limit=30):
    """获取真实金融新闻，失败时降级"""
    news = fetch_sina_realtime_news(limit)
    if not news or len(news) < 5:
        news = _get_mock_news(limit, source='财经快讯（离线）')
    return news[:limit]


# ==================== 样例数据 ====================

def fetch_sample_news(limit=30):
    """基于本地数据集生成样例新闻（用于展示系统能力）"""
    return _get_mock_news(limit, source='样例数据')


# ==================== 模拟数据（离线降级） ====================

def _get_mock_news(n=20, source='财经快讯'):
    """生成模拟金融新闻"""
    positive_templates = [
        "{company}预计全年净利润同比增长超过{N}%",
        "{company}与合作伙伴签署战略合作协议",
        "{company}成功中标{N}亿元重大工程项目",
        "{company}获得{N}亿元战略投资",
        "{company}新研发中心正式投产运营",
        "{company}获得核心发明专利授权",
        "机构看好{company}发展前景，目标价上调{N}%",
        "{company}回购{N}万股公司股份",
        "{company}分红方案获股东大会通过",
        "{company}新业务板块营收同比增长{N}%",
        "{company}拟投资{N}亿元扩建生产基地",
        "北向资金大幅加仓{company}",
        "{company}创新药获批上市",
        "{company}国际业务取得重大突破",
        "{company}成功登陆资本市场",
    ]
    negative_templates = [
        "{company}预计全年净利润同比下滑{N}%",
        "{company}收到证监会立案调查通知书",
        "{company}控股股东拟减持不超过{N}%的股份",
        "{company}因信息披露违规被出具警示函",
        "{company}商誉减值{N}亿元导致巨亏",
        "{company}主要产品被曝质量问题",
        "{company}被列入失信被执行人名单",
        "{company}终止定向增发计划",
        "{company}海外项目遭遇政策风险",
        "{company}股价连续跌停",
        "{company}应收账款高企坏账风险加大",
        "{company}行业竞争加剧毛利率持续下滑",
        "{company}被多家机构下调评级",
        "{company}资金链紧张短期偿债压力加大",
        "{company}供应商集中度风险引发市场担忧",
    ]
    neutral_templates = [
        "{company}发布年度报告",
        "{company}召开临时股东大会",
        "{company}董事会换届选举结果公布",
        "{company}公告业绩说明会安排",
        "{company}回应投资者关于{issue}的提问",
        "{company}完成工商变更登记",
        "{company}调整内部组织架构",
        "{company}变更公司证券事务代表",
        "{company}披露月份经营数据",
        "{company}高管团队赴{issue}调研考察",
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
        template = random.choice(
            positive_templates if category == 'positive'
            else negative_templates if category == 'negative'
            else neutral_templates
        )
        title = template.format(
            company=random.choice(companies),
            N=random.choice(numbers),
            issue=random.choice(['分红计划', '股价走势', '业绩波动', '并购传闻']),
        )
        hours_ago = random.randint(0, 72)
        news_time = (datetime.now() - timedelta(hours=hours_ago)).strftime('%Y-%m-%d %H:%M:%S')
        news_list.append({
            'title': title, 'time': news_time, 'source': source, 'url': '', '_mock': True,
        })

    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list


# ==================== 板块情绪 ====================

def get_stock_sectors_summary(news_results=None):
    """
    根据新闻分析结果生成板块情绪汇总
    如果传入新闻结果，则基于实际新闻生成；否则生成示例
    """
    if news_results and len(news_results) > 0:
        # 基于实际新闻生成板块情绪
        sectors_keywords = {
            '银行': ['银行', '工行', '建行', '农行', '中行', '交行', '招行'],
            '证券': ['证券', '券商', '中信', '海通', '华泰', '广发'],
            '保险': ['保险', '平安', '太保', '人保', '国寿'],
            '房地产': ['地产', '万科', '碧桂园', '恒大', '保利', '绿地'],
            '白酒': ['白酒', '茅台', '五粮液', '泸州老窖', '洋河'],
            '新能源汽车': ['新能源', '电动车', '比亚迪', '宁德', '锂电', '特斯拉'],
            '光伏': ['光伏', '太阳能', '隆基', '通威', '阳光电源'],
            '芯片': ['芯片', '半导体', '集成电路', '中芯', '台积电'],
            '医药': ['医药', '药明', '恒瑞', '生物', '制药', '医疗'],
            '消费电子': ['消费电子', '手机', '苹果', '华为', '小米'],
            '军工': ['军工', '航天', '船舶', '兵器', '中航'],
            '有色': ['有色', '铜', '铝', '黄金', '稀土'],
            '钢铁': ['钢铁', '宝钢', '鞍钢', '马钢'],
            '煤炭': ['煤炭', '煤', '中国神华', '中煤'],
            '电力': ['电力', '国家电网', '华能', '核电'],
            '农业': ['农业', '种业', '牧原', '温氏'],
            '传媒': ['传媒', '游戏', '影视', '出版'],
            '计算机': ['计算机', '云计算', '大数据', 'AI', '人工智能'],
            '通信': ['通信', '5G', '中国移动', '中国联通', '中国电信'],
            '机械': ['机械', '工程机械', '三一', '中联'],
            '化工': ['化工', '石化', '万华', '恒力'],
            '建材': ['建材', '水泥', '玻璃', '海螺'],
            '纺织': ['纺织', '服装', '丝绸'],
            '石油': ['石油', '石化', '中海油', '中石油'],
        }

        sector_results = []
        for sector, keywords in sectors_keywords.items():
            sector_news = []
            for r in news_results:
                title = r.get('title', '')
                if any(kw in title for kw in keywords):
                    sector_news.append(r)

            if len(sector_news) > 0:
                pos = sum(1 for n in sector_news if n.get('sentiment') == 'positive')
                neg = sum(1 for n in sector_news if n.get('sentiment') == 'negative')
                total = len(sector_news)
                score = (pos - neg) / total if total > 0 else 0

                sector_results.append({
                    'sector': sector,
                    'sentiment_score': round(score, 3),
                    'news_count': total,
                    'signal': 'buy' if score > 0.2 else ('sell' if score < -0.2 else 'neutral'),
                })

        sector_results.sort(key=lambda x: x['sentiment_score'], reverse=True)
        return sector_results

    # 无数据时生成示例
    sectors = ['银行', '证券', '保险', '房地产', '白酒', '新能源汽车',
               '光伏', '芯片', '医药', '消费电子', '军工', '有色',
               '钢铁', '煤炭', '电力', '石油', '农业', '传媒',
               '计算机', '通信', '机械', '化工', '建材', '纺织']
    results = []
    for sector in sectors:
        sentiment_score = random.uniform(-1, 1)
        results.append({
            'sector': sector,
            'sentiment_score': round(sentiment_score, 3),
            'news_count': random.randint(3, 25),
            'signal': 'buy' if sentiment_score > 0.2 else ('sell' if sentiment_score < -0.2 else 'neutral'),
        })
    results.sort(key=lambda x: x['sentiment_score'], reverse=True)
    return results
