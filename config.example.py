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

    # ── 消息推送（P3）────────────────────────────────────────────────────────
    # 三个渠道均可独立启用，enabled=False 时该渠道不推送
    "notify": {

        # 钉钉机器人（推荐）
        # 创建方式：钉钉群 → 智能群助手 → 添加机器人 → 自定义 → 加签模式
        "dingtalk": {
            "enabled": False,
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN",
            "secret": "YOUR_SECRET",   # 加签密钥，不用加签则填 "" 或删除
        },

        # 邮件（SMTP）
        # 以 QQ 邮件为例：smtp_host=smtp.qq.com, port=465, password=授权码（非登录密码）
        "email": {
            "enabled": False,
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
            "username": "your@qq.com",
            "password": "YOUR_AUTH_CODE",
            "to_addrs": ["your@qq.com"],
        },

        # Server酱（微信推送）：https://sct.ftqq.com 注册后获取 SendKey
        "serverchan": {
            "enabled": False,
            "sendkey": "YOUR_SENDKEY",
        },

        # 飞书机器人 Webhook
        # 创建方式：飞书群 → 群设置 → 机器人 → 添加机器人 → 自定义机器人
        # 安全设置选"签名校验"时填 secret；仅 IP 白名单时 secret 留空
        "feishu": {
            "enabled": False,
            "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_ID",
            "secret": "",   # 签名校验密钥，不启用则留空
        },
    },
}
