# -*- coding: utf-8 -*-
"""
A股选股系统 - 竞价分析模块
用于9:15-9:25集合竞价阶段二次筛选
"""

import requests
import pandas as pd
from datetime import datetime


def get_auction_data(ts_code):
    """获取股票集合竞价数据"""
    data = get_tencent_data(ts_code)
    if data:
        return data
    data = get_eastmoney_data(ts_code)
    return data


def get_tencent_data(ts_code):
    """使用腾讯API获取股票数据"""
    # 腾讯实时行情 ~ 分隔字段索引:
    # [0]市场 [1]名称 [2]代码 [3]现价 [4]昨收 [5]今开 [6]总量(手) [7]外盘 [8]内盘
    # [9]买1价 [10]买1量 [11]买2价 [12]买2量 ... [19]卖1价 [20]卖1量 ...
    # [29]时间 [30]涨跌额 [31]涨幅% [32]最高 [33]最低
    try:
        code = ts_code.replace('.SH', 'sh').replace('.SZ', 'sz')
        url = f"http://qt.gtimg.cn/q={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.text and 'v_' in response.text:
            parts = response.text.split('"')[1].split('~')
            if len(parts) > 33:
                pre_close = float(parts[4]) if parts[4] else 0
                open_price = float(parts[5]) if parts[5] else 0
                current_price = float(parts[3]) if parts[3] else open_price
                high = float(parts[32]) if parts[32] else current_price
                low = float(parts[33]) if parts[33] else open_price
                bid_vol1 = float(parts[10]) if parts[10] else 0
                ask_vol1 = float(parts[20]) if parts[20] else 0
                order_ratio = 0
                if (bid_vol1 + ask_vol1) > 0:
                    order_ratio = (bid_vol1 - ask_vol1) / (bid_vol1 + ask_vol1) * 100
                return {
                    'ts_code': ts_code,
                    'pre_close': pre_close,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'current': current_price,
                    'volume': float(parts[6]) if parts[6] else 0,
                    'amount': 0,
                    'turnover': 0,
                    'auction_price': 0,
                    'auction_vol': 0,
                    'auction_amount': 0,
                    'bid_price1': float(parts[9]) if parts[9] else 0,
                    'bid_vol1': bid_vol1,
                    'ask_price1': float(parts[19]) if parts[19] else 0,
                    'ask_vol1': ask_vol1,
                    'order_ratio': order_ratio,
                }
    except Exception as e:
        print(f"腾讯API获取{ts_code}失败: {e}")
    return None


def get_eastmoney_data(ts_code):
    """使用东方财富API获取股票数据"""
    try:
        code = ts_code.replace('.SH', '').replace('.SZ', '')
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': f"1.{code}" if code.startswith('6') else f"0.{code}",
            'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f169,f170,f171,f173,f174,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194,f195,f196,f197,f198,f199,f200,f201,f202,f203,f204,f205,f206,f207,f208,f209,f210'
        }
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        if data['data']:
            d = data['data']
            def safe_float(val, default=0):
                try:
                    if val is None or val == '':
                        return default
                    return float(val)
                except:
                    return default
            result = {
                'ts_code': ts_code,
                'pre_close': safe_float(d.get('f43'), 0) / 100,
                'open': safe_float(d.get('f44'), 0) / 100,
                'high': safe_float(d.get('f45'), 0) / 100,
                'low': safe_float(d.get('f46'), 0) / 100,
                'volume': safe_float(d.get('f47'), 0),
                'amount': safe_float(d.get('f48'), 0),
                'turnover': safe_float(d.get('f50'), 0) / 100,
                'auction_price': safe_float(d.get('f169'), 0) / 100,
                'auction_vol': safe_float(d.get('f170'), 0),
                'auction_amount': safe_float(d.get('f171'), 0),
                'bid_price1': safe_float(d.get('f173'), 0) / 100,
                'bid_vol1': safe_float(d.get('f174'), 0),
                'ask_price1': safe_float(d.get('f177'), 0) / 100,
                'ask_vol1': safe_float(d.get('f178'), 0),
            }
            if result['pre_close'] > 0 and result['auction_price'] > 0:
                result['auction_chg'] = (result['auction_price'] - result['pre_close']) / result['pre_close'] * 100
            else:
                result['auction_chg'] = 0
            result['volume_ratio'] = result['auction_vol'] / 10000 if result['auction_vol'] > 0 else 0
            bid_total = result.get('bid_vol1', 0)
            ask_total = result.get('ask_vol1', 0)
            if (bid_total + ask_total) > 0:
                result['order_ratio'] = (bid_total - ask_total) / (bid_total + ask_total) * 100
            else:
                result['order_ratio'] = 0
            return result
    except Exception as e:
        print(f"获取{ts_code}竞价数据失败: {e}")
    return None


def analyze_auction(ts_code):
    """分析竞价结果，返回评分和建议"""
    data = get_auction_data(ts_code)
    if not data:
        return None
    score = 0
    signals = []
    advice = "观望"
    auction_chg = data.get('auction_chg', 0)
    volume_ratio = data.get('volume_ratio', 0)
    order_ratio = data.get('order_ratio', 0)
    pre_close = data.get('pre_close', 0)
    open_price = data.get('open', 0)

    auction_price = data.get('auction_price', 0)
    is_valid_auction = False
    if auction_price > 0 and pre_close > 0:
        temp_chg = (auction_price - pre_close) / pre_close * 100
        is_valid_auction = -50 < temp_chg < 100

    if not is_valid_auction and open_price > 0 and pre_close > 0:
        auction_chg = (open_price - pre_close) / pre_close * 100
        change_type = "开盘"
    else:
        change_type = "竞价"

    if 2 <= auction_chg <= 4:
        score += 3
        signals.append(f"{change_type}温和")
    elif 4 < auction_chg <= 6:
        score += 2
        signals.append(f"{change_type}较强")
    elif auction_chg < 0:
        score -= 2
        signals.append(f"{change_type}低开")
    elif auction_chg > 8:
        score -= 3
        signals.append(f"{change_type}高开过多")

    if volume_ratio > 3:
        score += 3
        signals.append("量比活跃")
    elif volume_ratio > 1.5:
        score += 2
        signals.append("量比正常")
    elif volume_ratio > 0.5:
        score += 1
        signals.append("量比一般")
    else:
        score -= 1
        signals.append("量比不足")

    if order_ratio > 20:
        score += 2
        signals.append("买盘强劲")
    elif order_ratio > 0:
        score += 1
        signals.append("买盘占优")
    elif order_ratio < -20:
        score -= 2
        signals.append("卖盘强劲")

    current_price = data.get('current', open_price)
    if auction_chg > 3 and current_price < open_price:
        advice = "观望"
        signals.append("高开回落")
        score -= 3

    if score >= 7:
        advice = "强烈买入"
    elif score >= 4:
        advice = "建议买入"
    elif score >= 0:
        advice = "观望"
    else:
        advice = "放弃"

    risk = []
    if auction_chg > 5:
        risk.append("高开风险")
    elif auction_chg > 3:
        risk.append("高开中等风险")
    if auction_chg < 0:
        risk.append("低开")
    if auction_chg > 3 and current_price < open_price:
        risk.append("高开回落")
    if volume_ratio > 5:
        risk.append("量比异常")
    if order_ratio < -30:
        risk.append("卖盘过重")

    return {
        'ts_code': ts_code,
        'auction_price': open_price if not is_valid_auction else auction_price,
        'auction_chg': auction_chg,
        'volume_ratio': volume_ratio,
        'order_ratio': order_ratio,
        'score': score,
        'signals': ','.join(signals) if signals else '',
        'advice': advice,
        'risk': ','.join(risk) if risk else ''
    }


def filter_by_auction(stock_list):
    """根据竞价数据筛选股票"""
    results = []
    print(f"\n开始竞价分析，共{len(stock_list)}只股票...")
    for stock in stock_list:
        ts_code = stock.get('ts_code')
        if not ts_code:
            continue
        result = analyze_auction(ts_code)
        if result:
            result['name'] = stock.get('name', '')
            result['pre_close'] = stock.get('close', 0)
            result['score_total'] = stock.get('score', 0) + result['score']
            results.append(result)
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df = df.sort_values('score_total', ascending=False)
    return df


def get_auction_report(stock_list):
    """生成竞价分析报告"""
    df = filter_by_auction(stock_list)
    if df.empty:
        return "今日无符合竞价条件的股票", df
    report = []
    report.append("=" * 70)
    report.append(f"⚡ 竞价分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 70)
    report.append("\n【竞价买入建议】")
    report.append("-" * 50)

    strong_buy = df[df['advice'] == '强烈买入']
    if not strong_buy.empty:
        report.append(f"\n🔥 强烈买入 ({len(strong_buy)}只)")
        for _, row in strong_buy.head(3).iterrows():
            report.append(f"  {row['name']} ({row['ts_code']})")
            report.append(f"    竞价: {row['auction_price']:.2f} ({row['auction_chg']:+.2f}%)")
            report.append(f"    量比: {row['volume_ratio']:.1f} | 委比: {row['order_ratio']:+.1f}%")
            report.append(f"    竞价分: {row['score']} | 综合分: {row['score_total']}")

    buy = df[(df['advice'] == '建议买入') & (df['advice'] != '强烈买入')]
    if not buy.empty:
        report.append(f"\n✅ 建议买入 ({len(buy)}只)")
        for _, row in buy.head(5).iterrows():
            report.append(f"  {row['name']} ({row['ts_code']}) - {row['auction_chg']:+.2f}%")

    watch = df[df['advice'] == '观望']
    if not watch.empty:
        report.append(f"\n⚠️ 观望 ({len(watch)}只)")
        for _, row in watch.head(3).iterrows():
            report.append(f"  {row['name']} ({row['ts_code']}) - {row['auction_chg']:+.2f}%")

    skip = df[df['advice'] == '放弃']
    if not skip.empty:
        report.append(f"\n❌ 放弃 ({len(skip)}只)")
        for _, row in skip.head(3).iterrows():
            report.append(f"  {row['name']} ({row['ts_code']}) - {row['auction_chg']:+.2f}%")
            if row['risk']:
                report.append(f"    风险: {row['risk']}")

    report.append("\n" + "=" * 70)
    return '\n'.join(report), df

if __name__ == "__main__":
    test_stocks = [
        {'ts_code': '600773.SH', 'name': '西藏城投', 'score': 10},
        {'ts_code': '002549.SZ', 'name': '凯美特气', 'score': 15},
    ]
    report, df = get_auction_report(test_stocks)
    print(report)
