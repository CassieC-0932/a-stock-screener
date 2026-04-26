# -*- coding: utf-8 -*-
"""
A股选股系统 - 技术分析模块
"""

import logging
import pandas as pd
import numpy as np
from data_fetcher import get_daily_data, get_previous_trade_day

logger = logging.getLogger(__name__)


def calculate_ma(df, periods=[5, 10, 20, 60]):
    """计算移动平均线"""
    df = df.copy()
    for period in periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    return df


def calculate_ema(df, periods=[12, 26]):
    """计算指数移动平均线"""
    df = df.copy()
    for period in periods:
        df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    df = df.copy()
    df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
    df['diff'] = df['ema_fast'] - df['ema_slow']
    df['dea'] = df['diff'].ewm(span=signal, adjust=False).mean()
    df['macd'] = (df['diff'] - df['dea']) * 2
    return df


def calculate_kdj(df, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    df = df.copy()
    low_list = df['low'].rolling(window=n, min_periods=1).min()
    high_list = df['high'].rolling(window=n, min_periods=1).max()
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    df['kdj_k'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['kdj_d'] = df['kdj_k'].ewm(com=m2-1, adjust=False).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
    return df


def calculate_rsi(df, period=14):
    """计算RSI指标"""
    df = df.copy()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df[f'rsi{period}'] = 100 - (100 / (1 + rs))
    return df


def calculate_boll(df, period=20, std_dev=2):
    """计算布林带"""
    df = df.copy()
    df['boll_mid'] = df['close'].rolling(window=period).mean()
    df['boll_std'] = df['close'].rolling(window=period).std()
    df['boll_upper'] = df['boll_mid'] + std_dev * df['boll_std']
    df['boll_lower'] = df['boll_mid'] - std_dev * df['boll_std']
    return df


def calculate_volume_ratio(df):
    """计算量比"""
    df = df.copy()
    df['vol_ma5'] = df['vol'].rolling(window=5).mean()
    df['volume_ratio'] = df['vol'] / df['vol_ma5']
    return df


def detect_ma_cross(df):
    """检测MA金叉死叉"""
    if len(df) < 2:
        return None, None
    golden_cross = (df['ma5'].iloc[-1] > df['ma10'].iloc[-1] and 
                   df['ma5'].iloc[-2] <= df['ma10'].iloc[-2])
    death_cross = (df['ma5'].iloc[-1] < df['ma10'].iloc[-1] and 
                   df['ma5'].iloc[-2] >= df['ma10'].iloc[-2])
    return golden_cross, death_cross


def detect_macd_cross(df):
    """检测MACD金叉死叉"""
    if len(df) < 2:
        return None, None
    golden_cross = (df['diff'].iloc[-1] > df['dea'].iloc[-1] and 
                   df['diff'].iloc[-2] <= df['dea'].iloc[-2])
    death_cross = (df['diff'].iloc[-1] < df['dea'].iloc[-1] and 
                   df['diff'].iloc[-2] >= df['dea'].iloc[-2])
    return golden_cross, death_cross


def detect_breakout(df):
    """检测突破"""
    if len(df) < 5:
        return False, None
    latest = df.iloc[-1]
    ma20 = df['ma20'].iloc[-1]
    high_20 = df['high'].rolling(20).max().iloc[-1]
    breakout = latest['close'] > high_20 and latest['vol'] > df['vol'].mean() * 1.5
    return breakout, "20日高点" if breakout else None


def analyze_technical(ts_code, days=60):
    """综合技术分析"""
    start_date = get_previous_trade_day(days)
    df = get_daily_data(ts_code, start_date)
    if df.empty or len(df) < 20:
        return None

    df = calculate_ma(df)
    df = calculate_macd(df)
    df = calculate_kdj(df)
    df = calculate_rsi(df)
    df = calculate_boll(df)
    df = calculate_volume_ratio(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    analysis = {
        'ts_code': ts_code,
        'close': latest['close'],
        'pct_chg': latest['pct_chg'],
        'volume_ratio': latest.get('volume_ratio', 0),
        'ma5': latest['ma5'],
        'ma10': latest['ma10'],
        'ma20': latest['ma20'],
        'macd': latest['macd'],
        'kdj_k': latest['kdj_k'],
        'kdj_d': latest['kdj_d'],
        'kdj_j': latest['kdj_j'],
        'rsi14': latest['rsi14'],
        'boll_upper': latest['boll_upper'],
        'boll_lower': latest['boll_lower'],
    }

    ma_golden, ma_death = detect_ma_cross(df)
    macd_golden, macd_death = detect_macd_cross(df)
    breakout, breakout_type = detect_breakout(df)

    score = 0
    signals = []

    if macd_golden:
        score += 1
        signals.append("MACD金叉")

    if latest['kdj_k'] > latest['kdj_d'] and prev['kdj_k'] <= prev['kdj_d']:
        score += 1
        signals.append("KDJ金叉")

    if latest.get('volume_ratio', 0) > 2:
        score += 1
        signals.append("量价齐升")

    if latest['close'] > latest['ma20'] and latest['vol'] > df['vol'].mean():
        score += 1
        signals.append("突破20日均线")

    if latest['rsi14'] < 30 or (latest['rsi14'] > prev['rsi14'] and prev['rsi14'] < 30):
        score += 1
        signals.append("RSI反弹")

    if latest['close'] <= latest['boll_lower']:
        score += 1
        signals.append("布林下轨")

    analysis['score'] = score
    analysis['signals'] = signals

    if score >= 3 and macd_golden:
        analysis['buy_signal'] = "强烈买入"
        analysis['entry_point'] = "MACD金叉 + 量价齐升"
    elif score >= 2:
        analysis['buy_signal'] = "建议买入"
        analysis['entry_point'] = "技术面支撑"
    else:
        analysis['buy_signal'] = "观望"
        analysis['entry_point'] = None

    return analysis

if __name__ == "__main__":
    result = analyze_technical('000001.SZ')
    if result:
        print(f"股票: {result['ts_code']}")
        print(f"收盘价: {result['close']}")
        print(f"涨幅: {result['pct_chg']}%")
        print(f"技术评分: {result['score']}")
        print(f"买入信号: {result['buy_signal']}")
        print(f"信号: {result['signals']}")
