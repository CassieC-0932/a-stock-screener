# -*- coding: utf-8 -*-
"""
A股选股系统 - 数据获取模块

支持东方财富、新浪、腾讯三个数据源。
新增：PE/PB/行业批量字段，带缓存的 A 股交易日历。
"""

import json
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── 模块级缓存 ────────────────────────────────────────────────────────────────
_stock_basic_cache: pd.DataFrame = pd.DataFrame()
_stock_basic_cache_ts: Optional[datetime] = None
_CACHE_TTL_SECONDS = 300  # 5 分钟内复用，避免同次运行重复请求

_trade_date_cache: List[str] = []   # 降序排列的交易日字符串列表 "YYYYMMDD"


# ── 交易日历 ──────────────────────────────────────────────────────────────────

def get_trade_date_list() -> List[str]:
    """
    获取 A 股历史交易日列表（降序），结果进程内缓存。
    优先使用 AKShare；失败则退化为按周历估算（不含节假日）。
    """
    global _trade_date_cache
    if _trade_date_cache:
        return _trade_date_cache
    try:
        import akshare as ak
        df = ak.tool_trade_date_hist_sina()
        dates = (
            df['trade_date'].astype(str)
            .str.replace('-', '', regex=False)
            .sort_values(ascending=False)
            .tolist()
        )
        _trade_date_cache = dates
        logger.info("交易日历加载完成，共 %d 个交易日", len(dates))
        return dates
    except Exception as e:
        logger.warning("AKShare 交易日历获取失败（%s），退化为周历估算", e)
    return []


def get_recent_trade_days(n: int) -> List[str]:
    """
    返回过去 n 个交易日（降序，最近在前）。
    有完整日历时精确；否则仅排除周末。
    """
    dates = get_trade_date_list()
    today = datetime.now().strftime('%Y%m%d')
    past = [d for d in dates if d < today]
    if past:
        return past[:n]
    # 降级：排除周末
    result, cursor = [], datetime.now()
    while len(result) < n:
        cursor -= timedelta(days=1)
        if cursor.weekday() < 5:
            result.append(cursor.strftime('%Y%m%d'))
    return result


def get_previous_trade_day(n: int = 1) -> str:  # noqa: E501
    """
    返回第 n 个交易日之前的日期字符串（用作 K 线拉取起始日）。
    n=90 → 90 个交易日前的日期。
    """
    dates = get_trade_date_list()
    today = datetime.now().strftime('%Y%m%d')
    past = [d for d in dates if d < today]
    if n <= len(past):
        return past[n - 1]
    # 降级：1.5 倍日历天数 + 15 天节假日缓冲
    return (datetime.now() - timedelta(days=int(n * 1.5) + 15)).strftime('%Y%m%d')


# ── 股票列表（含 PE / PB / 行业）────────────────────────────────────────────────

def get_stock_basic_with_mv() -> pd.DataFrame:
    """获取全量 A 股基本信息 - 东方财富数据源（含 PE/PB/行业）"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        all_stocks = []
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        # f9=PE(TTM)  f23=PB  f100=所属行业
        params = {
            'pn': 1, 'pz': 5000, 'po': 1, 'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2, 'invt': 2, 'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f2,f3,f4,f5,f6,f7,f9,f12,f14,f20,f21,f23,f100'
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
                    logger.debug("获取第 %d 页，累计 %d / %d", pn, len(all_stocks), total)
                else:
                    break
            except Exception:
                break
            if len(all_stocks) >= total:
                break

        if all_stocks:
            df = pd.DataFrame(all_stocks)
            column_mapping = {
                'f12': 'ts_code', 'f14': 'name',
                'f2': 'close', 'f3': 'pct_chg', 'f4': 'change',
                'f5': 'vol', 'f6': 'amount', 'f7': 'turnover_rate',
                'f9': 'pe_ttm', 'f20': 'total_mv', 'f21': 'circ_mv',
                'f23': 'pb', 'f100': 'industry',
            }
            existing = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing)

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
            for col in ['close', 'pct_chg', 'vol', 'amount', 'turnover_rate', 'pe_ttm', 'pb']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            for col in ['total_mv', 'circ_mv']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce') / 100000000
            logger.info("东方财富全量行情获取完成：%d 只股票", len(df))
            return df
    except Exception as e:
        logger.error("获取股票数据失败: %s", e)
    return pd.DataFrame()


def get_stock_basic() -> pd.DataFrame:  # noqa
    """获取股票基本信息（5 分钟内结果复用）"""
    global _stock_basic_cache, _stock_basic_cache_ts
    now = datetime.now()
    if (
        not _stock_basic_cache.empty
        and _stock_basic_cache_ts is not None
        and (now - _stock_basic_cache_ts).total_seconds() < _CACHE_TTL_SECONDS
    ):
        return _stock_basic_cache
    result = get_stock_basic_with_mv()
    if not result.empty:
        _stock_basic_cache = result
        _stock_basic_cache_ts = now
    return result


# ── K 线数据 ──────────────────────────────────────────────────────────────────

def get_daily_data(ts_code: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    """获取日 K 线数据 - 东方财富"""
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
            records = []
            for kline in data['data']['klines']:
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
        logger.debug("获取 %s K线失败: %s", ts_code, e)
    return pd.DataFrame()


def get_kline_tencent(code: str, count: int = 90) -> pd.DataFrame:
    """获取日 K 线数据 - 腾讯数据源"""
    try:
        prefix = 'sh' if code.startswith('6') else 'sz'
        url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
               f"?param={prefix}{code},day,,,{count},qfq")
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = resp.json()
        klines = data['data'].get(f'{prefix}{code}', {}).get('qfqday', [])
        if not klines:
            return pd.DataFrame()
        records = [
            {'trade_date': k[0], 'open': float(k[1]), 'close': float(k[2]),
             'high': float(k[3]), 'low': float(k[4]), 'vol': float(k[5]), 'pct_chg': 0}
            for k in klines
        ]
        df = pd.DataFrame(records)
        if len(df) > 1:
            df['pct_chg'] = df['close'].pct_change() * 100
        return df
    except Exception:
        return pd.DataFrame()


# ── 新浪数据源 ────────────────────────────────────────────────────────────────

def get_all_stock_codes_sina() -> pd.DataFrame:
    """获取所有 A 股代码列表 - 新浪数据源"""
    stocks = []
    page_size = 80
    for page in range(1, 75):
        try:
            url = (f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                   f"Market_Center.getHQNodeData?page={page}&num={page_size}"
                   f"&sort=nmc&asc=1&node=hs_a&_s_r_a=sort")
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
                if price <= 0:
                    continue
                stocks.append({
                    'code': code, 'name': name, 'price': price,
                    'settlement': settlement,
                    'pct_chg': float(item.get('changepercent', 0)),
                    'nmc': float(item.get('nmc', 0)) / 10000,
                    'mktcap': float(item.get('mktcap', 0)) / 10000,
                    'turnover_rate': float(item.get('turnoverratio', 0)),
                })
            time.sleep(0.2)
        except Exception as e:
            logger.warning("新浪第 %d 页失败: %s", page, e)
            break
    logger.info("新浪获取到 %d 只股票", len(stocks))
    return pd.DataFrame(stocks)


# ── 指数 ──────────────────────────────────────────────────────────────────────

def get_realtime_quotes(ts_codes=None) -> pd.DataFrame:
    return get_stock_basic()


def get_index_daily(index_code: str = '000001', start_date: Optional[str] = None) -> pd.DataFrame:
    """获取指数日 K 线"""
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
        response = requests.get(url, params={'User-Agent': 'Mozilla/5.0'}, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = response.json()
        if data['data'] and data['data']['klines']:
            records = []
            for kline in data['data']['klines']:
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
        logger.error("获取指数数据失败: %s", e)
    return pd.DataFrame()
