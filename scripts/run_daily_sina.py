#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股选股系统 - 新浪数据源版本 v2
修复：早盘阶段使用昨收价，直接使用新浪返回的流通市值
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime
import time
import json
from data_fetcher import get_kline_tencent, get_all_stock_codes_sina as get_all_stock_codes


def analyze_stock(code, name, kline_df):
    """分析单只股票"""
    if kline_df.empty or len(kline_df) < 30:
        return None

    df = kline_df.copy()
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

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    if pd.isna(latest['ma10']) or latest['close'] < latest['ma10']:
        if pd.isna(latest['ma5']) or pd.isna(latest['ma10']) or latest['ma5'] <= latest['ma10']:
            return None

    score = 5
    signals = []
    warnings = []
    category = "稳健"

    if len(df) >= 20:
        p_min = df['close'].iloc[-20:].min()
        m_min = df['macd'].iloc[-20:].min()
        if latest['close'] <= p_min * 1.02 and latest['macd'] >= m_min and latest['macd'] > prev['macd']:
            score += 5
            signals.append("MACD底背离")
            category = "反弹"

    vol_ma5 = latest['vol_ma5'] if pd.notna(latest['vol_ma5']) and latest['vol_ma5'] > 0 else 1
    vol_ratio = latest['vol'] / vol_ma5
    if vol_ratio < 0.8 and latest['close'] < prev['close']:
        score += 3
        signals.append("缩量回调")
        if category == "稳健":
            category = "反弹"

    if len(df) >= 5 and df.iloc[-3]['close'] > df.iloc[-2]['close'] > latest['close']:
        if latest['close'] < df.iloc[-5]['close']:
            score += 3
            signals.append("超跌反弹")
            if category == "稳健":
                category = "反弹"

    ma60 = latest['ma60'] if pd.notna(latest['ma60']) else latest['close']
    price_vs_ma60 = (latest['close'] - ma60) / ma60 * 100 if ma60 > 0 else 0
    is_low = price_vs_ma60 < 10

    growth = (pd.notna(latest['ma5']) and pd.notna(latest['ma20']) and
              latest['ma5'] > latest['ma20'] and latest['close'] > latest['ma20'])
    if is_low and growth:
        score += 5
        signals.append("低位成长")
        category = "成长"

    if (pd.notna(latest['diff']) and pd.notna(latest['dea']) and
        pd.notna(prev['diff']) and pd.notna(prev['dea']) and
        latest['diff'] > latest['dea'] and prev['diff'] <= prev['dea']):
        score += 3
        signals.append("MACD金叉")
        if category == "稳健":
            category = "突破"

    if len(df) >= 3:
        up = sum(1 for i in range(-3, 0) if 0 < df.iloc[i]['pct_chg'] < 3)
        if up >= 2:
            score += 3
            signals.append("小阳慢涨")

    if len(df) >= 3 and df.iloc[-3]['close'] < df.iloc[-2]['close'] < latest['close']:
        score += 2
        signals.append("连涨")

    if pd.notna(latest['ma20']) and latest['close'] >= latest['ma20'] * 0.95:
        score += 2
        signals.append("MA20支撑")

    if 0.8 <= vol_ratio <= 1.5:
        score += 2

    if pd.notna(latest['macd']) and latest['macd'] > 0:
        score += 1

    if vol_ratio > 2:
        warnings.append("爆量")
    if pd.notna(latest['ma20']) and latest['close'] > latest['ma20'] * 1.15:
        warnings.append("远离均线")
    if price_vs_ma60 > 30:
        warnings.append("高位")

    return {
        'code': code, 'name': name,
        'close': latest['close'], 'pct_chg': latest['pct_chg'],
        'score': score,
        'signals': ','.join(signals) if signals else '-',
        'warnings': ','.join(warnings) if warnings else '',
        'category': category, 'is_low': is_low,
        'vol_ratio': round(vol_ratio, 2),
        'ma5': round(latest['ma5'], 2) if pd.notna(latest['ma5']) else 0,
        'ma10': round(latest['ma10'], 2) if pd.notna(latest['ma10']) else 0,
        'ma60': round(latest['ma60'], 2) if pd.notna(latest['ma60']) else 0,
        'price_vs_ma60': round(price_vs_ma60, 1),
    }


def run():
    print(f"=== A股选股系统 v2 {datetime.now()} ===\n")

    stocks = get_all_stock_codes()
    if stocks.empty:
        return "获取股票列表失败"

    df = stocks[(stocks['price'] > 0) & (stocks['price'] < 25)]
    df = df[(df['nmc'] > 20) & (df['nmc'] < 500)]
    print(f"基础筛选后: {len(df)} 只")

    if df.empty:
        df = stocks[(stocks['price'] > 0) & (stocks['price'] < 25)]
        df = df[(df['nmc'] > 10) & (df['nmc'] < 800)]
        print(f"放宽市值后: {len(df)} 只")

    if df.empty:
        return "无股票通过筛选"

    # 按流通市值升序截取（小市值优先），避免固定随机种子每天选同一批
    candidates = df.sort_values('nmc').head(600) if len(df) > 600 else df

    print(f"开始技术分析 ({len(candidates)} 只)...")
    results = []
    failed = 0

    for idx, row in candidates.iterrows():
        kline = get_kline_tencent(row['code'], count=90)
        if kline.empty or len(kline) < 30:
            failed += 1
            continue
        result = analyze_stock(row['code'], row['name'], kline)
        if result:
            result['pct_chg_today'] = row['pct_chg']
            result['nmc'] = round(row['nmc'], 1)
            results.append(result)
        time.sleep(0.12)

    print(f"分析完成: {len(results)} 只通过, {failed} 只数据不足")

    if not results:
        return "今日无符合条件的股票"

    results_df = pd.DataFrame(results).sort_values('score', ascending=False).head(15)

    report = []
    report.append("📈 A股智能选股报告")
    report.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")
    report.append("筛选: 低位成长股 + MACD底背离/缩量回调/超跌反弹")
    report.append(f"分析: {len(candidates)} 只 → 入选 {len(results_df)} 只")
    report.append("─" * 50)

    for cat in ['成长', '反弹', '突破', '稳健']:
        cat_df = results_df[results_df['category'] == cat]
        if cat_df.empty:
            continue
        report.append(f"\n【{cat}】")
        for _, row in cat_df.iterrows():
            pos = "低位" if row['is_low'] else ("高位" if row['price_vs_ma60'] > 30 else "中部")
            report.append(f"\n{row['name']} ({row['code']})")
            report.append(f"  现价: {row['close']:.2f} | 评分: {row['score']} | 流通市值: {row['nmc']:.0f}亿")
            report.append(f"  位置: {pos} (离MA60: {row['price_vs_ma60']:+.1f}%)")
            if row['ma5'] > 0:
                report.append(f"  MA5: {row['ma5']:.2f} MA10: {row['ma10']:.2f} MA60: {row['ma60']:.2f}")
            report.append(f"  信号: {row['signals']}")
            if row['warnings']:
                report.append(f"  ⚠️ {row['warnings']}")

    report.append("\n─" * 50)
    report.append("⚠️ 仅供参考，不构成投资建议")
    report.append("建议仓位≤30%，设止盈止损")

    report_text = "\n".join(report)
    print("\n" + report_text)

    # 保存
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(report_dir, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    with open(os.path.join(report_dir, f"{today}.txt"), 'w') as f:
        f.write(report_text)
    with open(os.path.join(report_dir, f"{today}.json"), 'w') as f:
        json.dump({'date': today, 'count': len(results_df), 'stocks': results_df.to_dict('records')}, f, ensure_ascii=False, indent=2)

    return report_text

if __name__ == "__main__":
    run()
