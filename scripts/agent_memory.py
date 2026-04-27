# -*- coding: utf-8 -*-
"""
Agent 记忆模块

读取持仓跟踪历史，统计各信号/类别的实际盈亏表现，
生成供 agent_brain 做决策的绩效记忆文件。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MEMORY_FILE = Path(__file__).parent / "reports" / "agent_memory.json"
_POSITIONS_FILE = Path(__file__).parent / "reports" / "positions.json"


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_memory() -> dict:
    """加载记忆文件，不存在则返回空白记忆。"""
    if _MEMORY_FILE.exists():
        try:
            with open(_MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("读取记忆文件失败: %s", e)
    return _blank_memory()


def _blank_memory() -> dict:
    return {
        "updated_at": None,
        "total_evaluated": 0,
        "win_rate": 0.5,
        "avg_return": 0.0,
        "signal_performance": {},
        "category_performance": {},
    }


def _save_memory(memory: dict) -> None:
    _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def _load_positions() -> list:
    if _POSITIONS_FILE.exists():
        try:
            with open(_POSITIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


# ── 核心：从持仓历史更新记忆 ──────────────────────────────────────────────────

def update_memory(price_map: Optional[dict] = None) -> dict:
    """
    遍历所有持仓记录，计算各信号/类别的平均收益和胜率，写入记忆。

    price_map: {ts_code: current_close}，用于估算未平仓浮动盈亏。
               传 None 时只统计已明确平仓（含 close_price）的记录。
    """
    positions = _load_positions()
    if not positions:
        return load_memory()

    samples = []
    for p in positions:
        entry = p.get('entry_price', 0)
        if entry <= 0:
            continue

        if p.get('status') == 'closed' and 'close_price' in p:
            pnl = (p['close_price'] - entry) / entry * 100
        elif p.get('status') == 'open' and price_map:
            current = price_map.get(p['ts_code'])
            if current:
                pnl = (current - entry) / entry * 100
            else:
                continue
        else:
            continue

        samples.append({
            'pnl': pnl,
            'signals': [s.strip() for s in p.get('signals', '').split(',') if s.strip()],
            'category': p.get('category', '未知'),
        })

    if not samples:
        logger.info("无有效持仓样本，记忆保持不变")
        return load_memory()

    # 汇总
    signal_stats: dict = {}
    category_stats: dict = {}
    total_return = 0.0
    wins = 0

    for s in samples:
        pnl = s['pnl']
        total_return += pnl
        if pnl > 0:
            wins += 1

        for sig in s['signals']:
            stat = signal_stats.setdefault(sig, {'total': 0.0, 'count': 0, 'wins': 0})
            stat['total'] += pnl
            stat['count'] += 1
            if pnl > 0:
                stat['wins'] += 1

        cat = s['category']
        stat = category_stats.setdefault(cat, {'total': 0.0, 'count': 0, 'wins': 0})
        stat['total'] += pnl
        stat['count'] += 1
        if pnl > 0:
            stat['wins'] += 1

    n = len(samples)
    memory = {
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "total_evaluated": n,
        "win_rate": round(wins / n, 4),
        "avg_return": round(total_return / n, 4),
        "signal_performance": {
            sig: {
                "avg_return": round(st['total'] / st['count'], 4),
                "win_rate": round(st['wins'] / st['count'], 4),
                "count": st['count'],
            }
            for sig, st in signal_stats.items()
        },
        "category_performance": {
            cat: {
                "avg_return": round(st['total'] / st['count'], 4),
                "win_rate": round(st['wins'] / st['count'], 4),
                "count": st['count'],
            }
            for cat, st in category_stats.items()
        },
    }

    _save_memory(memory)
    logger.info(
        "记忆更新完成：%d 条样本，胜率 %.1f%%，均收益 %.2f%%",
        n, memory['win_rate'] * 100, memory['avg_return'],
    )
    return memory
