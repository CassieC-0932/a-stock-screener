# -*- coding: utf-8 -*-
"""
A股选股系统 - 消息面分析模块

个股新闻：东方财富个股资讯 API，取最近 20 条标题做关键词情感打分。
市场情绪：统计全市场涨跌停数量与平均涨幅。
"""

import logging
import requests
import pandas as pd
from data_fetcher import get_stock_basic

logger = logging.getLogger(__name__)

# ── 情感词典 ──────────────────────────────────────────────────────────────────

_POSITIVE = [
    '利好', '突破', '增长', '盈利', '上涨', '合作', '中标', '获得', '创新高',
    '超预期', '涨停', '大单', '机构买入', '回购', '增持', '业绩大增', '扭亏',
    '新订单', '战略合作', '签约', '获批', '研发突破', '涨价', '提价',
]
_NEGATIVE = [
    '利空', '下跌', '亏损', '减持', '处罚', '违规', '风险', '跌停', '抛售',
    '起诉', '查处', '停产', '产能过剩', '竞争加剧', '降价', '退市风险',
    '业绩下滑', '爆雷', '诉讼', '被罚', '暴跌',
]


def _keyword_score(titles: list[str]) -> tuple[str, int]:
    """关键词情感打分，返回 (sentiment, score[-2,2])"""
    pos = sum(1 for t in titles for k in _POSITIVE if k in t)
    neg = sum(1 for t in titles for k in _NEGATIVE if k in t)
    total = pos + neg
    if total == 0:
        return 'neutral', 0
    ratio = (pos - neg) / total
    if ratio > 0.4:
        return 'positive', min(2, pos - neg)
    if ratio < -0.4:
        return 'negative', max(-2, neg - pos)
    return 'neutral', 0


# ── 个股新闻获取 ──────────────────────────────────────────────────────────────

def get_stock_news(ts_code: str, count: int = 20) -> list[str]:
    """
    获取个股最近 count 条新闻标题 - 东方财富个股资讯 API。
    返回标题列表；失败时返回空列表。
    """
    try:
        code = ts_code.replace('.SH', '').replace('.SZ', '')
        market = '1' if ts_code.endswith('.SH') else '0'
        url = "http://np-listapi.eastmoney.com/comm/web/getListInfo"
        params = {
            'client': 'web',
            'type': '1',
            'mTypeAndCode': f'{market}.{code}',
            'pageSize': count,
            'pageIndex': 1,
            'callback': '',
        }
        resp = requests.get(
            url, params=params,
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=8
        )
        data = resp.json()
        items = (data.get('data') or {}).get('list') or []
        titles = [str(item.get('title', '')) for item in items if item.get('title')]
        logger.debug("%s 获取到 %d 条新闻", ts_code, len(titles))
        return titles
    except Exception as e:
        logger.debug("获取 %s 新闻失败: %s", ts_code, e)
    return []


# ── 个股消息面分析 ────────────────────────────────────────────────────────────

def analyze_news_impact(ts_code: str) -> dict:
    """
    分析个股新闻情感，返回标准化结果。
    score: -2（极负面）~ 0（中性）~ 2（极正面）
    """
    result = {
        'ts_code': ts_code,
        'news_count': 0,
        'sentiment': 'neutral',
        'highlights': [],
        'score': 0,
    }
    titles = get_stock_news(ts_code)
    if not titles:
        return result

    result['news_count'] = len(titles)
    sentiment, score = _keyword_score(titles)
    result['sentiment'] = sentiment
    result['score'] = score

    # 筛出含情感词的标题作为亮点
    highlights = [
        t for t in titles
        if any(k in t for k in _POSITIVE + _NEGATIVE)
    ]
    result['highlights'] = highlights[:5]

    logger.debug(
        "%s 新闻情感: %s (score=%d, 正向=%d条)",
        ts_code, sentiment, score, len(highlights)
    )
    return result


# ── 市场整体情绪 ──────────────────────────────────────────────────────────────

def get_market_sentiment() -> dict:
    """
    计算当日市场情绪：上涨/下跌数量、涨跌停数量、平均涨幅。
    修正：涨停数基于全量行情统计（原代码永远为 0）。
    """
    result = {
        'index_change': 0.0,
        'up_count': 0,
        'down_count': 0,
        '涨停数': 0,
        '跌停数': 0,
        'sentiment': 'neutral',
    }
    try:
        all_stocks = get_stock_basic()
        if all_stocks.empty:
            return result

        pct = all_stocks['pct_chg'].dropna()
        result['up_count'] = int((pct > 0).sum())
        result['down_count'] = int((pct < 0).sum())
        result['index_change'] = round(float(pct.mean()), 2)
        result['涨停数'] = int((pct >= 9.9).sum())
        result['跌停数'] = int((pct <= -9.9).sum())

        if result['涨停数'] > 50 and result['index_change'] > 1:
            result['sentiment'] = 'bullish'
        elif result['跌停数'] > 30 or result['index_change'] < -1:
            result['sentiment'] = 'bearish'
        else:
            result['sentiment'] = 'neutral'

        logger.info(
            "市场情绪: %s | 涨:%d 跌:%d 涨停:%d 跌停:%d 均涨幅:%.2f%%",
            result['sentiment'], result['up_count'], result['down_count'],
            result['涨停数'], result['跌停数'], result['index_change']
        )
    except Exception as e:
        logger.error("获取市场情绪失败: %s", e)
    return result


# ── 热点板块 ──────────────────────────────────────────────────────────────────

def get_hot_sectors() -> pd.DataFrame:
    """按行业分组统计平均涨幅，返回前 10 热门行业"""
    try:
        all_stocks = get_stock_basic()
        if all_stocks.empty or 'industry' not in all_stocks.columns:
            return pd.DataFrame()
        sector_perf = (
            all_stocks.groupby('industry')
            .agg(avg_pct=('pct_chg', 'mean'), count=('ts_code', 'count'))
            .sort_values('avg_pct', ascending=False)
        )
        return sector_perf.head(10)
    except Exception as e:
        logger.warning("获取热点板块失败: %s", e)
    return pd.DataFrame()


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from log_config import setup_logging
    setup_logging()

    sentiment = get_market_sentiment()
    print(f"市场情绪: {sentiment}")

    sectors = get_hot_sectors()
    print(f"热点板块:\n{sectors}")

    news = analyze_news_impact('000001.SZ')
    print(f"个股新闻: {news}")
