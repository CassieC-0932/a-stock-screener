# -*- coding: utf-8 -*-
"""
A股选股系统 - 历史回测（修正版）

修复前视偏差：股票池用今日静态信息过滤（ST/交易所），
价格/MA 等条件全部从历史 K 线取当日数据计算，不使用实时行情。

已知局限：
- 用当前股票列表作为历史股票池，存在幸存者偏差（退市股被排除）
- 市值过滤需历史市值数据，K 线不包含，已移除该过滤条件
- 交易日历仅排除周末，不含中国法定节假日
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from log_config import setup_logging
from data_fetcher import get_stock_basic, get_daily_data, get_recent_trade_days

logger = logging.getLogger(__name__)


def get_static_filtered_stocks():
    """
    获取股票池：仅做静态过滤（ST/北交所/科创板），
    不使用任何实时价格字段，避免引入前视数据。
    """
    stocks = get_stock_basic()
    if stocks.empty:
        return pd.DataFrame()
    mask = (
        ~stocks['name'].str.contains('ST', na=False) &
        ~stocks['ts_code'].str.endswith('.BJ') &
        ~stocks['ts_code'].str.startswith('688')
    )
    return stocks[mask].reset_index(drop=True)


def check_conditions_on_date(ts_code, date):
    """
    用历史 K 线数据检查选股条件，无前视偏差。
    条件：当日收盘 < 130 元、未涨停、MA5>MA10>MA20 或站上 MA10。
    """
    try:
        start_date = (datetime.strptime(date, '%Y%m%d') - timedelta(days=90)).strftime('%Y%m%d')
        df = get_daily_data(ts_code, start_date, date)
        if df.empty or len(df) < 20:
            return False, None

        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        latest = df.iloc[-1]

        if latest['close'] >= 130:
            return False, None
        if latest['pct_chg'] >= 9.9:
            return False, None

        above_ma10 = latest['close'] > latest['ma10']
        ma_up = latest['ma5'] > latest['ma10'] > latest['ma20']
        if above_ma10 or ma_up:
            return True, latest['close']
    except Exception:
        pass
    return False, None


def backtest(days=5):
    """历史回测：对过去每个交易日模拟选股，统计次日涨跌"""
    print(f"=== 历史回测（过去 {days} 个交易日）===\n")
    trade_dates = get_recent_trade_days(days)
    print(f"回测日期（新→旧）: {trade_dates}\n")

    stocks = get_static_filtered_stocks()
    print(f"静态过滤后股票池: {len(stocks)} 只\n")
    if stocks.empty:
        return []

    results = []
    for date in trade_dates:
        print(f"--- 回测日期: {date} ---")
        selected = []
        for _, row in stocks.iterrows():
            passed, close_price = check_conditions_on_date(row['ts_code'], date)
            if passed:
                selected.append({'ts_code': row['ts_code'], 'name': row['name'], 'close': close_price})

        print(f"当日选出: {len(selected)} 只")
        if not selected:
            continue

        # 找次日（列表中下一个更早的日期）
        date_idx = trade_dates.index(date)
        if date_idx + 1 >= len(trade_dates):
            print("无次日数据，跳过")
            continue
        next_date = trade_dates[date_idx + 1]

        up, down = 0, 0
        for s in selected:
            try:
                kline = get_daily_data(s['ts_code'], next_date, next_date)
                if not kline.empty:
                    pct = kline.iloc[0]['pct_chg']
                    if pct > 0:
                        up += 1
                    else:
                        down += 1
            except Exception:
                pass

        if up + down > 0:
            accuracy = up / (up + down) * 100
            print(f"次日上涨: {up} 只  次日下跌: {down} 只  准确率: {accuracy:.1f}%")
            results.append({
                'date': date, 'selected': len(selected),
                'up': up, 'down': down, 'accuracy': accuracy
            })
        print()

    print("=" * 50)
    print("=== 回测汇总 ===")
    if results:
        total_up = sum(r['up'] for r in results)
        total_down = sum(r['down'] for r in results)
        overall = total_up / (total_up + total_down) * 100 if (total_up + total_down) > 0 else 0
        print(f"次日上涨合计: {total_up} 只  下跌合计: {total_down} 只  综合准确率: {overall:.1f}%")
        print("\n每日详情:")
        for r in results:
            print(f"  {r['date']}: 选 {r['selected']} 只，涨 {r['up']} 只 ({r['accuracy']:.1f}%)")
    else:
        print("无有效回测数据")
    return results


if __name__ == "__main__":
    setup_logging()
    backtest(5)
