# -*- coding: utf-8 -*-
"""
A股选股系统 - 基本面分析模块

两阶段：
  1. 批量过滤：PE/PB 来自东方财富全量行情（data_fetcher 已内置）
  2. 精细分析：ROE / 营收增速通过 AKShare 对候选股逐一查询
"""

import logging
import pandas as pd
from data_fetcher import get_stock_basic

logger = logging.getLogger(__name__)


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _safe_float(val, default=0.0) -> float:
    try:
        if val is None or str(val).strip() in ('', '-', '--', 'nan'):
            return default
        return float(str(val).replace('%', ''))
    except (ValueError, TypeError):
        return default


# ── 逐股财务指标（AKShare）────────────────────────────────────────────────────

def get_stock_financials(ts_code: str) -> dict:
    """
    通过 AKShare 获取单只股票的季报财务数据。
    返回字段：roe, net_margin, revenue_growth, debt_ratio
    仅在候选股精筛阶段调用，不用于全量扫描。
    """
    code = ts_code.replace('.SH', '').replace('.SZ', '')
    result = {'roe': None, 'net_margin': None, 'revenue_growth': None, 'debt_ratio': None}
    try:
        import akshare as ak
        # 财务分析综合指标（按报告期降序）
        df = ak.stock_financial_analysis_indicator(
            symbol=code,
            start_year=str(pd.Timestamp.now().year - 2)
        )
        if df.empty:
            return result
        row = df.iloc[0]
        result['roe'] = _safe_float(row.get('净资产收益率'))
        result['net_margin'] = _safe_float(row.get('销售净利率'))
        result['debt_ratio'] = _safe_float(row.get('资产负债率'))

        # 营收同比增速：取最近两期计算
        rev_col = next((c for c in df.columns if '营业总收入' in c or '营收' in c), None)
        if rev_col and len(df) >= 2:
            rev_curr = _safe_float(df.iloc[0][rev_col])
            rev_prev = _safe_float(df.iloc[1][rev_col])
            if rev_prev and rev_prev != 0:
                result['revenue_growth'] = (rev_curr - rev_prev) / abs(rev_prev) * 100
    except Exception as e:
        logger.debug("获取 %s 财务数据失败: %s", ts_code, e)
    return result


# ── 基础资格检查（无需 AKShare）──────────────────────────────────────────────

def get_stock_company(ts_code: str) -> dict:
    """从已缓存的行情数据中取单只股票基本信息"""
    stocks = get_stock_basic()
    if not stocks.empty:
        row = stocks[stocks['ts_code'] == ts_code]
        if not row.empty:
            return row.iloc[0].to_dict()
    return {}


def check_stock_eligibility(ts_code: str) -> dict:
    """资格检查：ST/停牌/涨跌停"""
    result = {'eligible': True, 'reasons': []}
    company = get_stock_company(ts_code)
    if not company:
        result['eligible'] = False
        result['reasons'].append("股票数据不存在")
        return result
    name = str(company.get('name', ''))
    if name.startswith('ST') or name.startswith('*ST'):
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


# ── 基本面评分（批量版）──────────────────────────────────────────────────────

def analyze_fundamental(ts_code: str, fetch_roe: bool = False) -> dict:
    """
    基本面综合评分（满分 10 分）。

    fetch_roe=False（默认）：仅用行情内的 PE/PB，适合批量筛选。
    fetch_roe=True：额外调用 AKShare 获取 ROE/营收增速，适合最终候选精筛。
    """
    result = {
        'ts_code': ts_code,
        'score': 0,
        'factors': [],
        'pe_ttm': None,
        'pb': None,
        'roe': None,
        'net_margin': None,
        'revenue_growth': None,
    }

    company = get_stock_company(ts_code)
    if not company:
        result['factors'].append("数据获取失败")
        return result

    result['company_name'] = company.get('name', '未知')
    pe = _safe_float(company.get('pe_ttm'))
    pb = _safe_float(company.get('pb'))
    turnover = _safe_float(company.get('turnover_rate'))
    circ_mv = _safe_float(company.get('circ_mv'))

    result['pe_ttm'] = pe
    result['pb'] = pb

    score = 0

    # PE 评分（0-3 分）
    if 0 < pe <= 20:
        score += 3
        result['factors'].append(f"PE低估({pe:.1f}x)")
    elif 20 < pe <= 40:
        score += 2
        result['factors'].append(f"PE合理({pe:.1f}x)")
    elif 40 < pe <= 60:
        score += 1
        result['factors'].append(f"PE偏高({pe:.1f}x)")
    elif pe < 0:
        result['factors'].append("亏损(PE<0)")

    # PB 评分（0-2 分）
    if 0 < pb <= 2:
        score += 2
        result['factors'].append(f"PB低估({pb:.2f}x)")
    elif 2 < pb <= 5:
        score += 1
        result['factors'].append(f"PB合理({pb:.2f}x)")

    # 换手率（0-2 分）
    if 2 <= turnover <= 10:
        score += 2
        result['factors'].append("换手率适中")
    elif 10 < turnover <= 20:
        score += 1
        result['factors'].append("换手率偏高")

    # 市值适中（0-1 分）
    if 50 <= circ_mv <= 500:
        score += 1
        result['factors'].append("市值适中")

    # ROE / 营收增速（需 AKShare，额外 0-2 分）
    if fetch_roe:
        fin = get_stock_financials(ts_code)
        result.update({k: v for k, v in fin.items() if v is not None})
        roe = fin.get('roe') or 0
        rev_growth = fin.get('revenue_growth') or 0
        if roe >= 15:
            score += 1
            result['factors'].append(f"ROE优秀({roe:.1f}%)")
        elif roe >= 8:
            score += 0.5
            result['factors'].append(f"ROE良好({roe:.1f}%)")
        if rev_growth >= 20:
            score += 1
            result['factors'].append(f"营收高增长({rev_growth:.1f}%)")
        elif rev_growth >= 5:
            score += 0.5
            result['factors'].append(f"营收稳增({rev_growth:.1f}%)")

    result['score'] = round(score, 1)
    return result
