# -*- coding: utf-8 -*-
"""
A股选股系统 - 配置文件

复制此文件为 config.py 后按需修改。
"""

CONFIG = {
    # 推荐数量
    "ultra_short_count": 3,   # 超短线（1-3天）
    "short_count": 5,          # 短线（3-7天）

    # 关注行业（与东方财富行业字段 f100 匹配）
    "focus_industries": [
        "电力", "电网", "电力设备", "电气设备",
        "半导体", "集成电路", "芯片",
        "光伏", "风电", "储能", "锂电池", "氢能",
        "算力", "人工智能", "云计算",
    ],

    # 推送时间 (HH:MM)
    "morning_push_time": "09:00",
    "evening_push_time": "15:30",

    # 超短线筛选条件
    "ultra_short": {
        "price_change_min": 3,    # 最小涨幅%
        "price_change_max": 7,    # 最大涨幅%
        "volume_ratio_min": 2,    # 最小量比
        "turnover_rate_min": 3,   # 最小换手率%
        "market_cap_max": 500,    # 最大流通市值(亿)
    },

    # 短线筛选条件
    "short": {
        "price_change_min": 1,
        "price_change_max": 10,
        "volume_ratio_min": 1.5,
        "turnover_rate_min": 2,
        "market_cap_max": 1000,
        "ma_cross": True,
        "volume_increase": 1.5,
    },

    # 风险控制
    "risk_control": {
        "max_position": 30,    # 单只最大仓位%
        "stop_loss": -5,       # 止损线%
        "take_profit": 10,     # 止盈线%
    },
}
