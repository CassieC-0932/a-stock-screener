# -*- coding: utf-8 -*-
"""
A股选股系统 - 基本面分析模块
"""

import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import get_stock_basic


def get_stock_company(ts_code):
    """获取公司基本信息"""
    stocks = get_stock_basic()
    if not stocks.empty:
        stock = stocks[stocks['ts_code'] == ts_code]
        if not stock.empty:
            return stock.iloc[0].to_dict()
    return {}


def analyze_fundamental(ts_code):
    """综合基本面分析"""
    result = {
        'ts_code': ts_code,
        'score': 0,
        'factors': []
    }

    company = get_stock_company(ts_code)
    if company:
        result['company_name'] = company.get('name', '未知')
        result['close'] = company.get('close', 0)
        result['pe'] = company.get('pe', 0)
        result['pb'] = company.get('pb', 0)
        result['total_mv'] = company.get('total_mv', 0)
        result['turnover_rate'] = company.get('turnover_rate', 0)

        score = 0
        if 3 <= result['turnover_rate'] <= 15:
            score += 1
            result['factors'].append("换手率适中")

        if 0 < result['pe'] < 50:
            score += 1
            result['factors'].append("估值合理")
        elif result['pe'] < 0:
            result['factors'].append("亏损")

        if 50 <= result['total_mv'] / 10000 < 500:
            score += 1
            result['factors'].append("市值适中")

        result['score'] = score
    else:
        result['score'] = 0
        result['factors'].append("数据获取失败")

    return result


def check_stock_eligibility(ts_code):
    """检查股票是否符合选股条件"""
    result = {
        'eligible': True,
        'reasons': []
    }

    company = get_stock_company(ts_code)
    if not company:
        result['eligible'] = False
        result['reasons'].append("股票数据不存在")
        return result

    name = company.get('name', '')
    if 'ST' in name or '*ST' in name or 'S' in name:
        result['eligible'] = False
        result['reasons'].append("ST股票风险高")
        return result

    if company.get('close', 0) == 0:
        result['eligible'] = False
        result['reasons'].append("停牌/退市")
        return result

    pct_chg = company.get('pct_chg', 0)
    if pct_chg >= 9.9:
        result['reasons'].append("已涨停，追高风险大")
    elif pct_chg <= -9.9:
        result['reasons'].append("已跌停，可能有大利空")

    return result

if __name__ == "__main__":
    stocks = get_stock_basic()
    if not stocks.empty:
        ts_code = stocks.iloc[0]['ts_code']
        result = analyze_fundamental(ts_code)
        print(f"基本面分析: {result}")
        eligibility = check_stock_eligibility(ts_code)
        print(f"资格检查: {eligibility}")
