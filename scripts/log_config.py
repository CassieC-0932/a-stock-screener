# -*- coding: utf-8 -*-
"""
日志配置模块

在入口脚本（run_daily.py / run_daily_sina.py / backtest.py）顶部调用
setup_logging() 即可全局生效。各子模块只需：

    import logging
    logger = logging.getLogger(__name__)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: Optional[str] = None,
) -> None:
    """
    配置全局日志。

    level       : 控制台输出级别（默认 INFO，调试时传 logging.DEBUG）
    log_to_file : 是否同时写入日志文件
    log_dir     : 日志目录，默认为 scripts/../logs/
    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_to_file:
        if log_dir is None:
            log_dir = str(Path(__file__).parent.parent / "logs")
        Path(log_dir).mkdir(exist_ok=True)
        log_file = Path(log_dir) / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, handlers=handlers)

    # 降低第三方库的噪音
    for noisy in ('urllib3', 'requests', 'akshare', 'charset_normalizer'):
        logging.getLogger(noisy).setLevel(logging.WARNING)
