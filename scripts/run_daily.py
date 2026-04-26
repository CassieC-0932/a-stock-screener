#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股选股系统 - 定时运行入口（东方财富数据源）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import logging
from datetime import datetime
from log_config import setup_logging
from stock_filter import apply_all_filters, get_all_a_stocks
from data_fetcher import get_stock_basic, get_market_environment
from portfolio_tracker import check_positions, save_positions

setup_logging()
logger = logging.getLogger(__name__)


def main():
    print(f"=== A股选股系统运行中... {datetime.now()} ===")

    try:
        # ── P1：显示持仓跟踪 ──────────────────────────────────────────────────
        stocks = get_stock_basic()
        position_report = check_positions(stocks)
        if "暂无持仓记录" not in position_report:
            print("\n" + position_report + "\n")

        # ── P0：大盘环境判断 ──────────────────────────────────────────────────
        env = get_market_environment()
        env_status = env['status']
        env_reason = env['reason']
        env_detail = env['detail']
        env_banner = {
            'bull':    "🟢 大盘偏强",
            'neutral': "🟡 大盘中性",
            'bear':    "🔴 大盘偏弱（熊市预警，建议降低仓位）",
            'unknown': "⚪ 大盘状态未知",
        }.get(env_status, "⚪ 大盘状态未知")
        print(f"\n{env_banner} | {env_reason}")
        if env_detail:
            d = env_detail
            print(f"   沪指: {d.get('close','N/A')}  MA5: {d.get('ma5','N/A')}  MA20: {d.get('ma20','N/A')}  近3日: {d.get('recent3_pct','N/A')}%\n")

        filtered = apply_all_filters(stocks)

        if filtered.empty:
            report = "今日无符合全部条件的股票"
        else:
            filtered = filtered.sort_values('pct_chg', ascending=False).head(10)
            report = []
            report.append("=" * 60)
            report.append(f"📈 A股智能选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            report.append("=" * 60)
            report.append(f"大盘环境: {env_banner} | {env_reason}")
            report.append("=" * 60)
            report.append("\n筛选条件:")
            report.append("1. 近15日非一字板涨停")
            report.append("2. 剔除ST/北交所/科创板")
            report.append("3. 流通市值 50-500亿")
            report.append("4. 股价 < 130元")
            report.append("5. 剔除今日涨停")
            report.append("6. MA453向上 + 站上MA10")
            report.append("7. 剔除近15日连续两天涨停")
            report.append("\n" + "-" * 60)
            report.append(f"符合条件股票: {len(filtered)} 只")
            report.append("-" * 60)

            for i, (_, row) in enumerate(filtered.iterrows(), 1):
                ma5 = row.get('ma5', 0) or 0
                ma10 = row.get('ma10', 0) or 0
                ma20 = row.get('ma20', 0) or 0
                ma60 = row.get('ma60', 0) or 0
                score = row.get('score', 0)
                signals = row.get('signals', '')
                warnings = row.get('warnings', '')
                price_vs_ma60 = row.get('price_vs_ma60', 0)
                position = "低位" if price_vs_ma60 < 10 else ("高位" if price_vs_ma60 > 30 else "中部")

                report.append(f"\n{i}. {row['name']} ({row['ts_code']})")
                report.append(f"   当前价: {row['close']:.2f} | 涨幅: {row['pct_chg']:.2f}% | 评分: {score}")
                report.append(f"   流通市值: {row.get('circ_mv', 0):.1f}亿 | 位置: {position}")
                if ma5:
                    report.append(f"   MA5: {ma5:.2f} | MA10: {ma10:.2f} | MA60: {ma60:.2f}")
                if signals:
                    report.append(f"   信号: {signals}")
                if warnings:
                    report.append(f"   ⚠️ 风险: {warnings}")

            report.append("\n" + "=" * 60)
            report.append("⚠️ 风险提示")
            report.append("-" * 40)
            report.append("1. 本系统仅供参考，不构成投资建议")
            report.append("2. 入场前请务必做好风险评估")
            report.append("3. 建议仓位不超过30%，设置止盈止损")
            report.append("4. 市场有风险，投资需谨慎")
            report.append("=" * 60)
            report = "\n".join(report)

        print("\n" + report)

        # 保存报告
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"{datetime.now().strftime('%Y-%m-%d')}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 保存JSON
        if not filtered.empty:
            json_data = filtered.to_dict('records')
        else:
            json_data = []
        json_file = os.path.join(report_dir, f"{datetime.now().strftime('%Y-%m-%d')}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stocks': json_data,
                'report': report
            }, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存到: {report_file}")

        # ── P1：将本次推荐写入持仓记录 ───────────────────────────────────────
        if not filtered.empty:
            added = save_positions(filtered)
            if added:
                print(f"已新增 {added} 只股票到持仓跟踪")

        return report

    except Exception as e:
        import traceback
        error_msg = f"选股系统运行失败: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg

if __name__ == "__main__":
    main()
