# -*- coding: utf-8 -*-
"""
A股选股系统 - 数据获取模块 (完整版)

支持东方财富、新浪、腾讯三个数据源。
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def get_stock_basic_with_mv():
    """获取股票基本信息（全量）- 东方财富数据源"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        all_stocks = []
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            'pn': 1, 'pz': 5000, 'po': 1, 'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2, 'invt': 2, 'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f2,f3,f4,f5,f6,f7,f12,f14,f20,f21'
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()

        total = data['data']['total']
        page_size = 500

        for pn in range(1, (total // page_size) + 2):
            params['pn'] = pn
            params['pz'] = page_size
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=10)
                dt = resp.json()
                if dt['data']['diff']:
                    all_stocks.extend(dt['data']['diff'])
                    print(f"获取第 {pn} 页... 累计 {len(all_stocks)} / {total}")
                else:
                    break
            except Exception:
                break
            if len(all_stocks) >= total:
                break

        if all_stocks:
            df = pd.DataFrame(all_stocks)
            column_mapping = {
                'f12': 'ts_code', 'f14': 'name', 'f2': 'close',
                'f3': 'pct_chg', 'f4': 'change', 'f5': 'vol',
                'f6': 'amount', 'f7': 'turnover_rate',
                'f20': 'total_mv', 'f21': 'circ_mv',
            }
            existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_cols)

            def add_suffix(code):
                code = str(code)
                if code.startswith('6'):
                    return code + '.SH'
                elif code.startswith('0') or code.startswith('3'):
                    return code + '.SZ'
                elif code.startswith('8'):
                    return code + '.BJ'
                return code + '.OTHER'

            df['ts_code'] = df['ts_code'].apply(add_suffix)
            for col in ['close', 'pct_chg', 'vol', 'amount', 'turnover_rate']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            for col in ['total_mv', 'circ_mv']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 100000000
            print(f"最终获取: {len(df)} 只股票")
            return df
    except Exception as e:
        print(f"获取股票数据失败: {e}")
    return pd.DataFrame()


def get_stock_basic():
    """获取股票基本信息"""
    return get_stock_basic_with_mv()


def get_previous_trade_day(n=1):
    """获取前n个交易日"""
    try:
        import akshare as ak
        df = ak.tool_trade_date_hist()
        dates = df['trade_date'].astype(str).sort_values(ascending=False).tolist()
        if n <= len(dates):
            return dates[n - 1]
    except Exception:
        pass
    return (datetime.now() - timedelta(days=n * 2)).strftime('%Y%m%d')


def get_daily_data(ts_code, start_date, end_date=None):
    """获取日K线数据 - 东方财富"""
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

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
                    'open': float(items[1]), 'close': float(items[2]),
                    'high': float(items[3]), 'low': float(items[4]),
                    'vol': float(items[5]), 'amount': float(items[6]),
                    'pct_chg': float(items[8]) if len(items) > 8 else 0
                })
            df = pd.DataFrame(records)
            df['ts_code'] = ts_code
            return df
    except Exception as e:
        print(f"获取{ts_code}K线失败: {e}")
    return pd.DataFrame()


def get_kline_tencent(code, count=90):
    """获取日K线数据 - 腾讯数据源"""
    try:
        prefix = 'sh' if code.startswith('6') else 'sz'
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{count},qfq"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = resp.json()
        klines = data['data'].get(f'{prefix}{code}', {}).get('qfqday', [])
        if not klines:
            return pd.DataFrame()
        records = []
        for item in klines:
            records.append({
                'trade_date': item[0],
                'open': float(item[1]), 'close': float(item[2]),
                'high': float(item[3]), 'low': float(item[4]),
                'vol': float(item[5]), 'pct_chg': 0,
            })
        df = pd.DataFrame(records)
        if len(df) > 1:
            df['pct_chg'] = df['close'].pct_change() * 100
        return df
    except Exception:
        return pd.DataFrame()


def get_all_stock_codes_sina():
    """获取所有A股代码列表 - 新浪数据源"""
    import json
    import time
    stocks = []
    page_size = 80

    for page in range(1, 75):
        try:
            url = (f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                   f"Market_Center.getHQNodeData?page={page}&num={page_size}&sort=nmc&asc=1&node=hs_a&_s_r_a=sort")
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            text = resp.text.strip()
            if not text or text == 'null':
                break
            data = json.loads(text)
            if not data:
                break
            for item in data:
                code = item.get('code', '')
                name = item.get('name', '')
                if 'ST' in name or '*ST' in name:
                    continue
                if code.startswith('9') or code.startswith('4') or code.startswith('688'):
                    continue
                settlement = float(item.get('settlement', 0))
                trade = float(item.get('trade', 0))
                price = trade if trade > 0 else settlement
                pct_chg = float(item.get('changepercent', 0))
                if price <= 0:
                    continue
                stocks.append({
                    'code': code, 'name': name, 'price': price,
                    'settlement': settlement, 'pct_chg': pct_chg,
                    'nmc': float(item.get('nmc', 0)) / 10000,
                    'mktcap': float(item.get('mktcap', 0)) / 10000,
                    'turnover_rate': float(item.get('turnoverratio', 0)),
                })
            time.sleep(0.2)
        except Exception as e:
            print(f"第{page}页失败: {e}")
            break
    print(f"新浪获取到 {len(stocks)} 只股票")
    return pd.DataFrame(stocks)


def get_realtime_quotes(ts_codes=None):
    """获取实时行情"""
    return get_stock_basic()


def get_index_daily(index_code='000001', start_date=None):
    """获取指数日K线"""
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
    try:
        code = index_code.replace('.SH', '').replace('.SZ', '')
        url = "http://32.push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'secid': f"1.{code}",
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': 101, 'fqt': 1,
            'beg': start_date,
            'end': datetime.now().strftime('%Y%m%d'),
            'lmt': 60
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
                    'open': float(items[1]), 'close': float(items[2]),
                    'high': float(items[3]), 'low': float(items[4]),
                    'vol': float(items[5]), 'amount': float(items[6]),
                    'pct_chg': float(items[8]) if len(items) > 8 else 0
                })
            return pd.DataFrame(records)
    except Exception as e:
        print(f"获取指数数据失败: {e}")
    return pd.DataFrame()
