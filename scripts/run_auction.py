#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股选股系统 - 竞价分析入口
用于9:15-9:30集合竞价阶段
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auction_analysis import get_auction_report, filter_by_auction
from datetime import datetime


def main():
    print(f"=== 竞价分析运行中... {datetime.now()} ===")
    try:
        report_file = f"reports/{datetime.now().strftime('%Y-%m-%d')}.json"
        if not os.path.exists(report_file):
            from datetime import timedelta
            yesterday = datetime.now() - timedelta(days=1)
            report_file = f"reports/{yesterday.strftime('%Y-%m-%d')}.json"
        if os.path.exists(report_file):
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stock_list = data.get('stocks', [])
                if not stock_list:
                    print("未找到昨日选股结果")
                    return
            print(f"读取到{len(stock_list)}只昨日选股")
            report, df = get_auction_report(stock_list)
            print("\n" + report)
            auction_file = f"reports/auction_{datetime.now().strftime('%Y-%m-%d')}.json"
            if not df.empty:
                df.to_json(auction_file, orient='records', force_ascii=False)
                print(f"\n竞价分析结果已保存到: {auction_file}")
            return report, df
        else:
            print("未找到昨日选股结果文件")
    except Exception as e:
        print(f"竞价分析失败: {e}")
        import traceback
        traceback.print_exc()
    return None, None

if __name__ == "__main__":
    main()
