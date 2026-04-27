#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股选股系统 - 定时运行入口（东方财富数据源）
集成 Agent 闭环：感知（大盘+记忆）→ 推理（brain）→ 行动（动态参数选股）→ 记录
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import logging
from datetime import datetime
from log_config import setup_logging
from stock_filter import apply_all_filters
from data_fetcher import get_stock_basic, get_market_environment
from portfolio_tracker import check_positions, save_positions
from agent_memory import load_memory, update_memory
from agent_brain import decide_params

setup_logging()
logger = logging.getLogger(__name__)


def main():
    print(f"=== A股选股系统运行中... {datetime.now()} ===")

    try:
        # ── 第一步：感知 - 拉取行情 ───────────────────────────────────────────
        stocks = get_stock_basic()

        # ── 第二步：感知 - 持仓跟踪（利用已有行情，无需二次请求）────────────────
        position_report = check_positions(stocks)
        if "暂无持仓记录" not in position_report:
            print("\n" + position_report + "\n")

        # ── 第三步：感知 - 大盘环境 ───────────────────────────────────────────
        env = get_market_environment()
        env_status = env['status']
        env_banner = {
            'bull':    "🟢 大盘偏强",
            'neutral': "🟡 大盘中性",
            'bear':    "🔴 大盘偏弱（熊市预警，建议降低仓位）",
            'unknown': "⚪ 大盘状态未知",
        }.get(env_status, "⚪ 大盘状态未知")
        print(f"\n{env_banner} | {env['reason']}")
        if env['detail']:
            d = env['detail']
            print(f"   沪指: {d.get('close')}  MA5: {d.get('ma5')}  MA20: {d.get('ma20')}  近3日: {d.get('recent3_pct')}%\n")

        # ── 第四步：感知 - 更新 Agent 记忆（用当前行情估算持仓浮动盈亏）─────────
        price_map = {}
        if not stocks.empty and 'ts_code' in stocks.columns:
            price_map = dict(zip(stocks['ts_code'], stocks['close']))
        memory = update_memory(price_map)

        # ── 第五步：推理 - Agent 大脑决策本次选股参数 ────────────────────────
        agent_params = decide_params(env, memory)
        max_count = agent_params['max_count']

        print(f"\n🤖 Agent 决策: {agent_params['rationale']}")
        if agent_params.get('score_boost'):
            boost_str = ', '.join(f"{k}({v:+d})" for k, v in agent_params['score_boost'].items())
            print(f"   信号动态权重: {boost_str}")
        if agent_params.get('preferred_categories'):
            print(f"   优选类别: {agent_params['preferred_categories']}")
        print(f"   准入门槛: score≥{agent_params['min_score']} | 推荐数量上限: {max_count}\n")

        # ── 第六步：行动 - 用动态参数执行选股 ───────────────────────────────
        filtered = apply_all_filters(stocks, agent_params=agent_params)

        # ── 第七步：生成报告 ──────────────────────────────────────────────────
        if filtered.empty:
            report = "今日无符合条件的股票"
        else:
            filtered = filtered.sort_values('score', ascending=False).head(max_count)
            report = []
            report.append("=" * 60)
            report.append(f"📈 A股智能选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            report.append("=" * 60)
            report.append(f"大盘环境: {env_banner} | {env['reason']}")
            report.append(f"🤖 Agent: {agent_params['rationale']}")
            report.append("=" * 60)
            report.append("\n筛选条件:")
            report.append("1. 近15日非一字板涨停")
            report.append("2. 剔除ST/北交所/科创板")
            report.append(f"3. 流通市值 {agent_params['market_cap_range'][0]}-{agent_params['market_cap_range'][1]}亿（Agent动态）")
            report.append("4. 股价 < 130元")
            report.append("5. 剔除今日涨停")
            report.append("6. MA453向上 + 站上MA10")
            report.append(f"7. 准入评分 ≥ {agent_params['min_score']}（Agent动态）")
            report.append("\n" + "-" * 60)
            report.append(f"符合条件股票: {len(filtered)} 只")
            report.append("-" * 60)

            for i, (_, row) in enumerate(filtered.iterrows(), 1):
                ma5 = row.get('ma5', 0) or 0
                ma10 = row.get('ma10', 0) or 0
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

            # Agent 决策明细（附在报告尾部供复盘）
            if memory['total_evaluated'] > 0:
                report.append("\n── Agent 记忆摘要 ──────────────────────────────")
                report.append(f"历史样本: {memory['total_evaluated']} 条 | 胜率: {memory['win_rate']:.1%} | 均收益: {memory['avg_return']:.2f}%")
                if memory.get('signal_performance'):
                    top = sorted(memory['signal_performance'].items(),
                                 key=lambda x: x[1]['avg_return'], reverse=True)[:3]
                    report.append("信号表现TOP3: " + ' | '.join(
                        f"{s}(均{p['avg_return']:.1f}%/胜{p['win_rate']:.0%})" for s, p in top
                    ))

            report = "\n".join(report)

        print("\n" + report)

        # ── 第八步：持久化 - 保存报告和 JSON ─────────────────────────────────
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, f"{datetime.now().strftime('%Y-%m-%d')}.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        json_file = os.path.join(report_dir, f"{datetime.now().strftime('%Y-%m-%d')}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stocks': filtered.to_dict('records') if not filtered.empty else [],
                'report': report,
                'agent_params': {k: v for k, v in agent_params.items() if k != 'detail'},
                'market_env': env,
                'memory_snapshot': {
                    'total_evaluated': memory['total_evaluated'],
                    'win_rate': memory['win_rate'],
                    'avg_return': memory['avg_return'],
                },
            }, f, ensure_ascii=False, indent=2)

        print(f"\n报告已保存到: {report_file}")

        # ── 第九步：记录 - 本次推荐写入持仓，供下次记忆学习 ──────────────────
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
