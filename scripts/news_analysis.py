# -*- coding: utf-8 -*-
"""
A股选股系统 - 消息面分析模块
"""

import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import get_stock_basic


def analyze_news_impact(ts_code):
    """分析新闻对股价的影响（简化版）"""
    result = {
        'ts_code': ts_code,
        'news_count': 0,
        'sentiment': 'neutral',
        'highlights': [],
        'score': 0
    }
    return result


def get_market_sentiment():
    """获取市场情绪"""
    result = {
        'index_change': 0,
        'up_count': 0,
        'down_count': 0,
        '涨停数': 0,
        '跌停数': 0,
        'sentiment': 'neutral'
    }
    try:
        all_stocks = get_stock_basic()
        if not all_stocks.empty:
            result['up_count'] = len(all_stocks[all_stocks['pct_chg'] > 0])
            result['down_count'] = len(all_stocks[all_stocks['pct_chg'] < 0])
            result['index_change'] = all_stocks['pct_chg'].mean()

        if result['涨停数'] > 50 and result['index_change'] > 1:
            result['sentiment'] = 'bullish'
        elif result['涨停数'] < 10 and result['index_change'] < -1:
            result['sentiment'] = 'bearish'
        else:
            result['sentiment'] = 'neutral'
    except Exception as e:
        print(f"获取市场情绪失败: {e}")
    return result


def get_hot_sectors():
    """获取热点板块"""
    try:
        all_stocks = get_stock_basic()
        if not all_stocks.empty and 'industry' in all_stocks.columns:
            sector_perf = all_stocks.groupby('industry').agg({
                'pct_chg': 'mean',
                'ts_code': 'count'
            }).rename(columns={'ts_code': 'count'})
            sector_perf = sector_perf.sort_values('pct_chg', ascending=False)
            return sector_perf.head(10)
    except Exception:
        pass
    return pd.DataFrame()

if __name__ == "__main__":
    sentiment = get_market_sentiment()
    print(f"市场情绪: {sentiment}")
    sectors = get_hot_sectors()
    print(f"热点板块: {len(sectors)}")
