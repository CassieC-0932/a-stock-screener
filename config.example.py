# -*- coding: utf-8 -*-
"""
A股选股系统 - 配置文件
"""

# Tushare Token
TUSHARE_TOKEN = "your_tushare_token_here"

# 选股参数
CONFIG = {
    # 股票池数量
    "ultra_short_count": 3,   # 超短线推荐数量
    "short_count": 5,          # 短线推荐数量
    
    # 关注板块
    "focus_industries": [
        "电力", "电网", "芯片", "能源", "算力",
        "电力设备", "电气设备", "半导体", "集成电路",
        "光伏", "风电", "锂电池", "氢能", "储能"
    ],
    
    # 推送时间 (HH:MM)
    "morning_push_time": "09:00",   # 早盘前
    "evening_push_time": "15:30",  # 收盘后
    
    # 超短线筛选条件
    "ultra_short": {
        "price_change_min": 3,    # 最小涨幅%
        "price_change_max": 7,    # 最大涨幅%
        "volume_ratio_min": 2,   # 最小量比
        "turnover_rate_min": 3,  # 最小换手率%
        "market_cap_max": 500,   # 最大市值(亿)
    },
    
    # 短线筛选条件
    "short": {
        "price_change_min": 1,
        "price_change_max": 10,
        "volume_ratio_min": 1.5,
        "turnover_rate_min": 2,
        "market_cap_max": 1000,
        "ma_cross": True,         # MA金叉
        "volume_increase": 1.5,  # 成交量放大倍数
    },
    
    # 风险控制
    "risk_control": {
        "max_position": 30,       # 单只股票最大仓位%
        "stop_loss": -5,         # 止损线%
        "take_profit": 10,       # 止盈线%
    }
}

# 行业代码映射 (Tushare)
INDUSTRY_CODES = {
    "电力": "SW0",
    "电网": "SW0",
    "芯片": "SW0",
    "能源": "SW0",
    "算力": "SW0",
    "电力设备": "SW0",
    "电气设备": "SW0",
    "半导体": "SW0",
    "集成电路": "SW0",
    "光伏": "SW0",
    "风电": "SW0",
    "锂电池": "SW0",
    "氢能": "SW0",
    "储能": "SW0",
}
