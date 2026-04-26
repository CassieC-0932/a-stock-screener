#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股复盘助手 - 分析选股结果
"""

import json
from datetime import datetime
from pathlib import Path


def analyze_stocks(json_path):
    """分析股票数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    stocks = data['stocks']
    date = data['date'].split()[0]
    print(f"📊 复盘日期: {date}")
    print(f"📈 选股数量: {len(stocks)} 只\n")

    gains = [s['pct_chg'] for s in stocks]
    avg_gain = sum(gains) / len(gains)
    max_gain = max(gains)
    min_gain = min(gains)

    up_count = sum(1 for g in gains if g > 0)
    down_count = sum(1 for g in gains if g < 0)
    flat_count = sum(1 for g in gains if g == 0)

    print("=" * 60)
    print("📊 涨跌统计")
    print("=" * 60)
    print(f"上涨数量: {up_count} 只 ({up_count/len(gains)*100:.1f}%)")
    print(f"下跌数量: {down_count} 只 ({down_count/len(gains)*100:.1f}%)")
    print(f"平盘数量: {flat_count} 只 ({flat_count/len(gains)*100:.1f}%)")
    print(f"平均涨幅: {avg_gain:.2f}%")
    print(f"最高涨幅: {max_gain:.2f}% ({stocks[gains.index(max_gain)]['name']})")
    print(f"最低涨幅: {min_gain:.2f}% ({stocks[gains.index(min_gain)]['name']})")
    print()

    print("=" * 60)
    print("📊 涨幅分布")
    print("=" * 60)
    gt9 = sum(1 for g in gains if g >= 9)
    gt8 = sum(1 for g in gains if 8 <= g < 9)
    gt7 = sum(1 for g in gains if 7 <= g < 8)
    gt6 = sum(1 for g in gains if 6 <= g < 7)
    print(f"≥9%: {gt9} 只")
    print(f"8%-9%: {gt8} 只")
    print(f"7%-8%: {gt7} 只")
    print(f"6%-7%: {gt6} 只")
    print()

    print("=" * 60)
    print("📊 按分类表现")
    print("=" * 60)
    categories = {}
    for s in stocks:
        cat = s['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s['pct_chg'])
    for cat, gains_list in sorted(categories.items()):
        avg = sum(gains_list) / len(gains_list)
        print(f"{cat}: {len(gains_list)} 只 | 平均涨幅: {avg:.2f}%")
    print()

    print("=" * 60)
    print("📊 按位置表现")
    print("=" * 60)
    low_pos = [s['pct_chg'] for s in stocks if s['is_low']]
    high_pos = [s['pct_chg'] for s in stocks if not s['is_low']]
    if low_pos:
        avg_low = sum(low_pos) / len(low_pos)
        print(f"低位: {len(low_pos)} 只 | 平均涨幅: {avg_low:.2f}%")
    if high_pos:
        avg_high = sum(high_pos) / len(high_pos)
        print(f"高位/中部: {len(high_pos)} 只 | 平均涨幅: {avg_high:.2f}%")
    print()

    print("=" * 60)
    print("📊 按MACD金叉表现")
    print("=" * 60)
    macd_golden = [s['pct_chg'] for s in stocks if s['macd_golden']]
    no_macd_golden = [s['pct_chg'] for s in stocks if not s['macd_golden']]
    if macd_golden:
        avg_macd = sum(macd_golden) / len(macd_golden)
        print(f"MACD金叉: {len(macd_golden)} 只 | 平均涨幅: {avg_macd:.2f}%")
    if no_macd_golden:
        avg_no_macd = sum(no_macd_golden) / len(no_macd_golden)
        print(f"无MACD金叉: {len(no_macd_golden)} 只 | 平均涨幅: {avg_no_macd:.2f}%")
    print()

    print("=" * 60)
    print("📊 按评分表现")
    print("=" * 60)
    score_groups = {}
    for s in stocks:
        score = s['score']
        if score not in score_groups:
            score_groups[score] = []
        score_groups[score].append(s['pct_chg'])
    for score in sorted(score_groups.keys()):
        gains_list = score_groups[score]
        avg = sum(gains_list) / len(gains_list)
        print(f"评分{score}: {len(gains_list)} 只 | 平均涨幅: {avg:.2f}%")
    print()

    print("=" * 60)
    print("📋 详细列表（按涨幅排序）")
    print("=" * 60)
    sorted_stocks = sorted(stocks, key=lambda x: x['pct_chg'], reverse=True)
    for i, s in enumerate(sorted_stocks, 1):
        print(f"{i:2d}. {s['name']:8s} ({s['ts_code']})")
        print(f"    涨幅: {s['pct_chg']:6.2f}% | 评分: {s['score']:2d} | 分类: {s['category']}")
        print(f"    位置: {'低位' if s['is_low'] else '高位/中部'} | MACD金叉: {'是' if s['macd_golden'] else '否'}")
        print(f"    信号: {s['signals'] if s['signals'] else '无'}")
        if s['warnings']:
            print(f"    ⚠️  {s['warnings']}")
        print()

    print("=" * 60)
    print("🔍 特征总结")
    print("=" * 60)
    print("表现最佳的特征:")
    top3 = sorted_stocks[:3]
    print("前3名共同特征:")
    for s in top3:
        print(f"  - {s['name']}: {s['pct_chg']:.2f}%, 分类={s['category']}, 位置={'低位' if s['is_low'] else '高位'}, MACD金叉={s['macd_golden']}")
    print()
    print("=" * 60)
    print("✅ 复盘完成")
    print("=" * 60)

if __name__ == "__main__":
    reports_dir = Path(__file__).parent / "reports"
    json_files = sorted(reports_dir.glob("*.json"), reverse=True)
    if not json_files:
        print(f"未找到报告文件，请先运行 run_daily.py 生成报告。目录: {reports_dir}")
    else:
        json_path = json_files[0]
        print(f"分析最新报告: {json_path.name}")
        analyze_stocks(json_path)
