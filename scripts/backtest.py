# -*- coding: utf-8 -*-
"""
A股选股系统 - 历史回测（基础版）
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def get_stock_basic():
    """获取股票基本信息"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        all_stocks = []
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        for pn in range(1, 13):
            params = {
                'pn': pn, 'pz': 500, 'po': 1, 'np': 1,
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': 2, 'invt': 2, 'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                'fields': 'f2,f3,f4,f5,f6,f7,f12,f14,f20,f21'
            }
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                dt = resp.json()
                if dt['data']['diff']:
                    all_stocks.extend(dt['data']['diff'])
                else:
                    break
            except Exception:
                break

        if all_stocks:
            df = pd.DataFrame(all_stocks)
            column_mapping = {
                'f12': 'ts_code', 'f14': 'name', 'f2': 'close',
                'f3': 'pct_chg', 'f4': 'change', 'f5': 'vol',
                'f6': 'amount', 'f7': 'turnover_rate',
                'f20': 'total_mv', 'f21': 'circ_mv',
            }
            df = df.rename(columns=column_mapping)
            def add_suffix(code):
                code = str(code)
                if code.startswith('6'):
                    return code + '.SH'
                elif code.startswith('0') or code.startswith('3'):
                    return code + '.SZ'
                return code + '.BJ'
            df['ts_code'] = df['ts_code'].apply(add_suffix)
            for col in ['close', 'pct_chg', 'vol', 'amount', 'turnover_rate']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            for col in ['total_mv', 'circ_mv']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 100000000
            return df
    except Exception as e:
        print(f"获取数据失败: {e}")
    return pd.DataFrame()


def get_daily_data(ts_code, start_date, end_date):
    """获取历史K线"""
    try:
        code = ts_code.replace('.SH', '').replace('.SZ', '')
        url = "http://32.push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'secid': f"1.{code}" if code.startswith('6') else f"0.{code}",
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': 101, 'fqt': 1, 'beg': start_date, 'end': end_date, 'lmt': 60
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        if data['data'] and data['data']['klines']:
            klines = data['data']['klines']
            records = []
            for kline in klines:
                items = kline.split(',')
                records.append({
                    'trade_date': items[0],
                    'close': float(items[2]),
                    'pct_chg': float(items[8]) if len(items) > 8 else 0
                })
            return pd.DataFrame(records)
    except Exception:
        pass
    return pd.DataFrame()


def get_trade_dates(days=5):
    """获取过去n个交易日"""
    dates = []
    today = datetime.now()
    for _ in range(days * 3):
        today -= timedelta(days=1)
        if today.weekday() < 5:
            dates.append(today.strftime('%Y%m%d'))
            if len(dates) >= days:
                break
    return dates


def filter_stocks(df):
    """筛选条件"""
    if df.empty:
        return df
    df = df[~df['name'].str.contains('ST', na=False)]
    df = df[~df['ts_code'].str.endswith('.BJ')]
    df = df[~df['ts_code'].str.startswith('688')]
    df = df[df['close'] < 25]
    df = df[df['pct_chg'] < 9.9]
    df = df[df['circ_mv'] > 50]
    df = df[df['circ_mv'] < 500]
    return df


def check_ma(ts_code, date):
    """检查MA条件"""
    try:
        start_date = (datetime.strptime(date, '%Y%m%d') - timedelta(days=60)).strftime('%Y%m%d')
        df = get_daily_data(ts_code, start_date, date)
        if df.empty or len(df) < 20:
            return False
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        latest = df.iloc[-1]
        above_ma10 = latest['close'] > latest['ma10']
        ma_up = latest['ma5'] > latest['ma10'] > latest['ma20']
        return above_ma10 and ma_up
    except Exception:
        return False


def backtest(days=5):
    """历史回测"""
    print(f"=== 历史回测 (过去{days}天) ===\n")
    trade_dates = get_trade_dates(days)
    print(f"交易日期: {trade_dates}\n")
    stocks = get_stock_basic()
    print(f"股票总数: {len(stocks)}")

    results = []
    for date in trade_dates:
        print(f"\n--- 回测日期: {date} ---")
        df = filter_stocks(stocks.copy())
        print(f"基础筛选后: {len(df)} 只")
        selected = []
        for _, row in df.iterrows():
            if check_ma(row['ts_code'], date):
                selected.append(row)
        print(f"MA筛选后: {len(selected)} 只")
        if not selected:
            continue
        next_date_idx = trade_dates.index(date) + 1
        if next_date_idx >= len(trade_dates):
            print("无次日数据，跳过")
            continue
        next_date = trade_dates[next_date_idx]
        up_count = 0
        down_count = 0
        for row in selected:
            try:
                kline = get_daily_data(row['ts_code'], next_date, next_date)
                if not kline.empty:
                    pct = kline.iloc[0]['pct_chg']
                    if pct > 0:
                        up_count += 1
                    else:
                        down_count += 1
            except Exception:
                pass
        if up_count + down_count > 0:
            accuracy = up_count / (up_count + down_count) * 100
            print(f"次日上涨: {up_count}只 ({accuracy:.1f}%)")
            print(f"次日下跌: {down_count}只")
            results.append({
                'date': date, 'selected': len(selected),
                'up': up_count, 'down': down_count, 'accuracy': accuracy
            })

    print("\n" + "=" * 50)
    print("=== 回测汇总 ===")
    total_selected = sum(r['selected'] for r in results)
    total_up = sum(r['up'] for r in results)
    total_down = sum(r['down'] for r in results)
    overall_accuracy = total_up / (total_up + total_down) * 100 if (total_up + total_down) > 0 else 0
    print(f"总选股次数: {total_selected}")
    print(f"次日上涨: {total_up}只 ({overall_accuracy:.1f}%)")
    print(f"次日下跌: {total_down}只")
    print("\n每日详情:")
    for r in results:
        print(f"  {r['date']}: 选{r['selected']}只，涨{r['up']}只 ({r['accuracy']:.1f}%)")
    return results

if __name__ == "__main__":
    results = backtest(5)
