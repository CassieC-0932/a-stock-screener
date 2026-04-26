#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股选股系统 - 自动调度入口

在每个交易日 15:35（收盘后）自动运行选股，并将报告推送到已配置的渠道。
使用方式：
    python3 scripts/scheduler.py          # 前台运行，Ctrl+C 停止
    nohup python3 scripts/scheduler.py &  # 后台运行
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from log_config import setup_logging
from data_fetcher import get_trade_date_list
from notifier import notify

setup_logging()
logger = logging.getLogger(__name__)

# 每个交易日几点运行（24 小时制）
_RUN_HOUR = 15
_RUN_MINUTE = 35


def _is_trade_day(date_str: str) -> bool:
    """判断给定日期是否是交易日"""
    dates = get_trade_date_list()
    return date_str in dates


def run_job():
    """定时任务主体：检查交易日 → 选股 → 推送"""
    today = datetime.now().strftime('%Y%m%d')
    if not _is_trade_day(today):
        logger.info("今日 %s 非交易日，跳过", today)
        return

    logger.info("====== 开始执行每日选股 (%s) ======", today)
    try:
        import run_daily
        report = run_daily.main()

        title = f"A股选股报告 {datetime.now().strftime('%Y-%m-%d')}"
        # 报告可能很长，推送时截取前 2000 字符
        content = str(report)[:2000] + ("\n…（报告已截断）" if len(str(report)) > 2000 else "")
        notify(title, content)
        logger.info("====== 每日选股完成 ======")
    except Exception as e:
        err_msg = f"选股任务异常: {e}"
        logger.exception(err_msg)
        notify("A股选股系统异常", err_msg)


def main():
    scheduler = BlockingScheduler(timezone='Asia/Shanghai')
    scheduler.add_job(
        run_job,
        trigger=CronTrigger(
            hour=_RUN_HOUR,
            minute=_RUN_MINUTE,
            day_of_week='mon-fri',   # 仅工作日触发；交易日由 run_job 内部二次校验
            timezone='Asia/Shanghai',
        ),
        id='daily_stock_screen',
        name='每日选股',
        misfire_grace_time=300,      # 允许最多 5 分钟延迟启动
        coalesce=True,               # 多次错过只补跑一次
    )

    next_run = scheduler.get_job('daily_stock_screen').next_run_time
    logger.info("调度器已启动，下次运行时间: %s", next_run)
    print(f"调度器已启动，每个交易日 {_RUN_HOUR:02d}:{_RUN_MINUTE:02d} 自动运行选股")
    print("按 Ctrl+C 停止\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("调度器已停止")


if __name__ == '__main__':
    main()
