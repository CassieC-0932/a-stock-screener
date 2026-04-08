# -*- coding: utf-8 -*-
"""
A股选股系统 - 选股过滤器（成长版）
重点：低位优质成长股 + 三大优化条件
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_fetcher import get_stock_basic, get_daily_data, get_previous_trade_day
import requests


def get_all_a_stocks():
    """获取所有A股"""
    stocks = get_stock_basic()
    if stocks.empty:
        return pd.DataFrame()

    def filter_stock(row):
        name = str(row.get('name', ''))
        ts_code = str(row.get('ts_code', ''))
        if 'ST' in name or '*ST' in name or 'S' in name:
            return False
        if ts_code.endswith('.BJ'):
            return False
        if ts_code.startswith('688'):
            return False
        return True

    df = stocks[stocks.apply(filter_stock, axis=1)]
    return df


def get_hot_sectors():
    """获取热门板块"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': 1, 'pz': 50, 'po': 1, 'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2, 'invt': 2, 'fid': 'f3',
            'fs': 'm:1+t:2,m:1+t:23',
            'fields': 'f2,f3,f12,f14'
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        if data['data'] and data['data']['diff']:
            sectors = []
            for item in data['data']['diff'][:30]:
                sectors.append(str(item.get('f14', '')))
            return sectors
    except Exception:
        pass
    return []


def filter_basic_conditions(df):
    """基础条件"""
    if df.empty:
        return df
    df = df[df['close'] < 25]
    df = df[df['pct_chg'] < 9.9]
    return df


def filter_by_market_cap(df, min_mv=30, max_mv=500):
    """市值筛选"""
    if df.empty:
        return df
    df = df[df['circ_mv'].notna()]
    df = df[df['circ_mv'] > min_mv]
    df = df[df['circ_mv'] < max_mv]
    return df


def analyze_growth_stock(ts_code, hot_sectors):
    """分析低位成长股"""
    start_date = get_previous_trade_day(90)
    df = get_daily_data(ts_code, start_date)
    if df.empty or len(df) < 30:
        return None

    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()

    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['diff'] = df['ema12'] - df['ema26']
    df['dea'] = df['diff'].ewm(span=9, adjust=False).mean()
    df['macd'] = (df['diff'] - df['dea']) * 2

    df['vol_ma5'] = df['vol'].rolling(5).mean()
    df['vol_ma20'] = df['vol'].rolling(20).mean()

    df['ma多头'] = (df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20']) & (df['ma20'] > df['ma60'])

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    prev2 = df.iloc[-3] if len(df) > 2 else prev

    score = 0
    signals = []
    category = ""

    above_ma10 = latest['close'] > latest['ma10']
    ma_up = latest['ma5'] > latest['ma10'] > latest['ma20']
    if not (above_ma10 or ma_up):
        return None
    score += 5

    if len(df) >= 20:
        price_low_20 = df['close'].rolling(20).min().iloc[-1]
        macd_low_20 = df['macd'].rolling(20).min().iloc[-1]
        price_new_low = latest['close'] <= price_low_20 * 1.02
        macd_not_new_low = latest['macd'] >= macd_low_20
        if price_new_low and macd_not_new_low and latest['macd'] > prev['macd']:
            score += 5
            signals.append("MACD底背离")
            category = "反弹"

    vol_ratio = latest['vol'] / latest['vol_ma5'] if latest['vol_ma5'] > 0 else 1
    price_down = latest['close'] < prev['close']
    if vol_ratio < 0.8 and price_down:
        score += 3
        signals.append("缩量回调")
        category = "反弹"

    if len(df) >= 3:
        if df.iloc[-3]['close'] > df.iloc[-2]['close'] > latest['close']:
            if latest['close'] < df.iloc[-5]['close']:
                score += 3
                signals.append("超跌反弹")
                category = "反弹"

    ma60 = latest.get('ma60', latest['close'])
    price_vs_ma60 = (latest['close'] - ma60) / ma60 * 100 if ma60 else 0
    is_low = price_vs_ma60 < 10

    low_60 = df['close'].rolling(60).min().iloc[-1]
    near_low = latest['close'] <= low_60 * 1.1

    growth_trend = latest['ma5'] > latest['ma20'] and latest['close'] > latest['ma20']

    if len(df) >= 5:
        recent_up = df.iloc[-5:]['close'].iloc[-1] > df.iloc[-5:]['close'].iloc[0] * 1.05

    if is_low and growth_trend:
        score += 5
        signals.append("低位成长")
        category = "成长"

    if is_low and near_low:
        score += 3
        signals.append("接近前低")

    if latest['close'] >= latest['ma20'] * 0.95:
        score += 2
        signals.append("MA20支撑")

    if len(df) >= 3:
        small_up_days = sum(1 for i in range(-3, 0) if 0 < df.iloc[i]['pct_chg'] < 3)
        if small_up_days >= 2:
            score += 3
            signals.append("小阳慢涨")

    macd_golden = (latest['diff'] > latest['dea']) and (prev['diff'] <= prev['dea'])
    if macd_golden:
        score += 3
        signals.append("MACD金叉")
        if not category:
            category = "突破"

    if 0.8 <= vol_ratio <= 1.5:
        score += 2

    if latest['macd'] > 0:
        score += 1

    if len(df) >= 3:
        if df.iloc[-3]['close'] < df.iloc[-2]['close'] < latest['close']:
            score += 2
            signals.append("连涨")

    warnings = []
    if vol_ratio > 2:
        warnings.append("爆量")
    if latest['close'] > latest['ma20'] * 1.15:
        warnings.append("远离均线")
    if price_vs_ma60 > 30:
        warnings.append("高位")

    if not category:
        category = "稳健"

    return {
        'score': score,
        'signals': signals,
        'warnings': warnings,
        'category': category,
        'is_low': is_low,
        'growth': growth_trend,
        'macd_golden': macd_golden,
        'vol_ratio': vol_ratio,
        'ma5': latest['ma5'],
        'ma10': latest['ma10'],
        'ma20': latest['ma20'],
        'ma60': ma60,
        'close': latest['close'],
        'price_vs_ma60': price_vs_ma60
    }


def apply_all_filters(stocks):
    """应用所有筛选"""
    print(f"原始股票数量: {len(stocks)}")
    df = get_all_a_stocks()
    print(f"剔除ST/北交所/科创板后: {len(df)}")
    if df.empty:
        return pd.DataFrame()

    df = filter_basic_conditions(df)
    print(f"股价/涨停筛选后: {len(df)}")
    if df.empty:
        return pd.DataFrame()

    hot_sectors = get_hot_sectors()
    print(f"热门板块: {hot_sectors[:5]}...")

    print("分析中...")
    results = []
    for idx, row in df.iterrows():
        ts_code = row['ts_code']
        try:
            analysis = analyze_growth_stock(ts_code, hot_sectors)
            if analysis:
                row['score'] = analysis['score']
                row['signals'] = ','.join(analysis['signals'])
                row['warnings'] = ','.join(analysis['warnings']) if analysis['warnings'] else ''
                row['category'] = analysis['category']
                row['is_low'] = analysis['is_low']
                row['growth'] = analysis['growth']
                row['macd_golden'] = analysis['macd_golden']
                row['vol_ratio'] = analysis['vol_ratio']
                row['ma5'] = analysis['ma5']
                row['ma10'] = analysis['ma10']
                row['ma20'] = analysis['ma20']
                row['ma60'] = analysis['ma60']
                row['price_vs_ma60'] = analysis['price_vs_ma60']
                results.append(row)
        except Exception:
            continue

    print(f"技术筛选后: {len(results)}")
    if not results:
        return pd.DataFrame()

    df_tech = pd.DataFrame(results)
    df_tech = df_tech.sort_values('score', ascending=False)

    df_final = filter_by_market_cap(df_tech, min_mv=30, max_mv=500)
    print(f"市值筛选后: {len(df_final)}")

    if len(df_final) < 10:
        df_final = filter_by_market_cap(df_tech, min_mv=20, max_mv=800)
        print(f"市值放宽后: {len(df_final)}")

    return df_final

if __name__ == "__main__":
    stocks = get_stock_basic()
    result = apply_all_filters(stocks)
    print(f"\n最终入选: {len(result)} 只")
    if not result.empty:
        print("\n=== 低位成长股 ===")
        low_growth = result[result['category'] == '成长']
        print(low_growth[['ts_code','name','close','score','signals']].head(10))
        print("\n=== 反弹股 ===")
        rebound = result[result['category'] == '反弹']
        print(rebound[['ts_code','name','close','score','signals']].head(10))
