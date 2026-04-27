# -*- coding: utf-8 -*-
"""
A股选股系统 - 持仓跟踪模块

记录每次推荐的入场价，跟踪持仓盈亏，触发止盈/止损提示。
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_POSITIONS_FILE = Path(__file__).parent / "reports" / "positions.json"
_STOP_LOSS_PCT = -5.0   # 止损线 %
_TAKE_PROFIT_PCT = 10.0  # 止盈线 %


# ── 持仓 I/O ──────────────────────────────────────────────────────────────────

def _load_positions() -> list:
    if _POSITIONS_FILE.exists():
        try:
            with open(_POSITIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("读取持仓文件失败: %s", e)
    return []


def _save_positions(positions: list) -> None:
    _POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_POSITIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)


# ── 对外接口 ──────────────────────────────────────────────────────────────────

def save_positions(df: pd.DataFrame, date: str = None) -> int:
    """
    将本次推荐股票写入持仓记录（已在跟踪的股票不重复添加）。
    返回新增持仓数量。
    """
    if df.empty:
        return 0
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    positions = _load_positions()
    existing = {p['ts_code'] for p in positions if p.get('status') == 'open'}

    new_count = 0
    for _, row in df.iterrows():
        code = str(row['ts_code'])
        if code in existing:
            continue
        positions.append({
            'ts_code': code,
            'name': str(row.get('name', '')),
            'entry_date': date,
            'entry_price': float(row['close']),
            'score': int(row.get('score', 0)),
            'signals': str(row.get('signals', '')),
            'status': 'open',
        })
        new_count += 1

    _save_positions(positions)
    logger.info("新增 %d 条持仓记录，当前共 %d 条未平仓", new_count, len(existing) + new_count)
    return new_count


def check_positions(current_prices: pd.DataFrame = None) -> str:
    """
    检查所有未平仓持仓的盈亏状态，返回格式化报告字符串。
    current_prices 为可选的股票行情 DataFrame（含 ts_code / close 列）；
    若未传入则自动拉取。
    """
    positions = _load_positions()
    open_pos = [p for p in positions if p.get('status') == 'open']
    if not open_pos:
        return "暂无持仓记录"

    if current_prices is None or current_prices.empty:
        from data_fetcher import get_stock_basic
        current_prices = get_stock_basic()

    price_map: dict = {}
    if not current_prices.empty and 'ts_code' in current_prices.columns:
        price_map = dict(zip(current_prices['ts_code'], current_prices['close']))

    lines = [
        "=" * 60,
        f"📊 持仓跟踪  （止损 {_STOP_LOSS_PCT}% / 止盈 +{_TAKE_PROFIT_PCT}%）",
        "=" * 60,
    ]

    for p in open_pos:
        code = p['ts_code']
        entry = p['entry_price']
        current = price_map.get(code)

        if current is None:
            pnl_str = "N/A（无行情）"
            action = ""
        else:
            pnl = (current - entry) / entry * 100
            pnl_str = f"{pnl:+.2f}%"
            if pnl <= _STOP_LOSS_PCT:
                action = "  ⛔ 建议止损"
            elif pnl >= _TAKE_PROFIT_PCT:
                action = "  ✅ 建议止盈"
            else:
                action = ""

        curr_str = f"{current:.2f}" if current is not None else "N/A"
        lines.append(
            f"{p['name']} ({code})  入场 {p['entry_date']} @ {entry:.2f}"
            f"  → 现价 {curr_str}  盈亏 {pnl_str}{action}"
        )

    lines.append("=" * 60)
    return "\n".join(lines)


def close_position(ts_code: str, exit_price: float = None, reason: str = "手动平仓") -> bool:
    """
    将指定股票的持仓标记为已平仓。
    exit_price: 实际出场价，记录后供 agent_memory 学习；不传则只标记状态。
    """
    positions = _load_positions()
    found = False
    for p in positions:
        if p['ts_code'] == ts_code and p.get('status') == 'open':
            p['status'] = 'closed'
            p['close_date'] = datetime.now().strftime('%Y-%m-%d')
            p['close_reason'] = reason
            if exit_price is not None:
                p['close_price'] = float(exit_price)
                p['pnl_pct'] = round(
                    (exit_price - p['entry_price']) / p['entry_price'] * 100, 4
                )
            found = True
    if found:
        _save_positions(positions)
        logger.info("平仓: %s @ %s（%s）", ts_code, exit_price or 'N/A', reason)
    return found


def get_open_positions() -> list:
    """返回所有未平仓持仓列表。"""
    return [p for p in _load_positions() if p.get('status') == 'open']
