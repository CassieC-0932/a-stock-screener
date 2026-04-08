# -*- coding: utf-8 -*-
"""
A股选股系统 - 推荐引擎
"""

import pandas as pd
from datetime import datetime
from config import CONFIG
from data_fetcher import get_stock_basic, get_previous_trade_day
from technical_analysis import analyze_technical
from fundamental_analysis import analyze_fundamental, check_stock_eligibility
from news_analysis import analyze_news_impact, get_market_sentiment


def get_stock_name(ts_code):
    """获取股票名称"""
    stocks = get_stock_basic()
    if not stocks.empty:
        stock = stocks[stocks['ts_code'] == ts_code]
        if not stock.empty:
            return stock.iloc[0]['name']
    return ts_code


def score_stock(row, market_sentiment):
    """综合评分选股"""
    scores = {'total': 0, 'technical': 0, 'fundamental': 0, 'news': 0, 'risk': 0}
    details = {
        'technical_signals': [], 'fundamental_factors': [],
        'news_highlights': [], 'risk_factors': []
    }

    ts_code = row['ts_code']
    eligibility = check_stock_eligibility(ts_code)
    if not eligibility['eligible']:
        return None, scores, details
    if eligibility['reasons']:
        details['risk_factors'].extend(eligibility['reasons'])

    pct_chg = row.get('pct_chg', 0)
    turnover_rate = row.get('turnover_rate', 0)
    close = row.get('close', 0)

    tech_score = 0
    signals = []
    if 1 <= pct_chg <= 8:
        tech_score += 2
        signals.append("涨幅适中")
    if 3 <= turnover_rate <= 15:
        tech_score += 2
        signals.append("换手率活跃")
    elif turnover_rate > 15:
        tech_score += 1
        signals.append("高换手")
    if 5 <= close <= 100:
        tech_score += 1
        signals.append("股价合理")

    scores['technical'] = tech_score * 4
    details['technical_signals'] = signals

    fund = analyze_fundamental(ts_code)
    scores['fundamental'] = fund.get('score', 0) * 3
    details['fundamental_factors'] = fund.get('factors', [])

    news = analyze_news_impact(ts_code)
    scores['news'] = (news.get('score', 0) + 1) * 10
    details['news_highlights'] = news.get('highlights', [])[:3]

    if market_sentiment.get('sentiment') == 'bullish':
        scores['risk'] += 10
    elif market_sentiment.get('sentiment') == 'bearish':
        scores['risk'] -= 5
    else:
        scores['risk'] += 5

    scores['total'] = scores['technical'] + scores['fundamental'] + scores['news'] + scores['risk']

    return {
        'ts_code': ts_code,
        'name': row.get('name', get_stock_name(ts_code)),
        'close': close, 'pct_chg': pct_chg,
        'volume_ratio': row.get('volume_ratio', turnover_rate),
        'turnover_rate': turnover_rate,
        'industry': row.get('industry', ''),
        'score': scores['total'],
        'buy_signal': '建议买入' if scores['total'] >= 30 else '观望',
        'entry_point': '分时突破' if pct_chg > 3 else '低吸',
        'signals': signals,
        'details': details
    }, scores, details


def select_ultra_short_stocks(stock_df, market_sentiment, limit=3):
    """超短线选股 (1-3天)"""
    results = []
    if stock_df.empty:
        return results
    for _, row in stock_df.iterrows():
        try:
            result, scores, details = score_stock(row, market_sentiment)
            if result is None:
                continue
            pct_chg = row.get('pct_chg', 0)
            turnover_rate = row.get('turnover_rate', 0)
            if 2 <= pct_chg <= 8 and turnover_rate >= 3 and scores['total'] >= 25:
                results.append(result)
        except Exception:
            continue
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]


def select_short_stocks(stock_df, market_sentiment, limit=5):
    """短线选股 (3-7天)"""
    results = []
    if stock_df.empty:
        return results
    for _, row in stock_df.iterrows():
        try:
            result, scores, details = score_stock(row, market_sentiment)
            if result is None:
                continue
            if scores['total'] >= 20:
                results.append(result)
        except Exception:
            continue
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]


def generate_recommendation_report(ultra_short, short, market_sentiment):
    """生成推荐报告"""
    report = []
    report.append("=" * 60)
    report.append(f"📈 A股智能选股报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 60)

    sentiment_text = {
        'bullish': '看涨 🔥', 'bearish': '看跌 ❄️', 'neutral': '中性'
    }.get(market_sentiment.get('sentiment', 'neutral'), '中性')
    report.append(f"\n🌡️ 市场情绪: {sentiment_text}")
    report.append(f"   大盘涨跌: {market_sentiment.get('index_change', 0):.2f}%")
    report.append(f"   上涨: {market_sentiment.get('up_count', 0)} 只")
    report.append(f"   下跌: {market_sentiment.get('down_count', 0)} 只")

    report.append(f"\n⚡ 超短线推荐 (1-3天) - 共{len(ultra_short)}只")
    report.append("-" * 40)
    if ultra_short:
        for i, stock in enumerate(ultra_short, 1):
            report.append(f"\n{i}. {stock['name']} ({stock['ts_code']})")
            report.append(f"   当前价: {stock['close']:.2f} | 涨幅: {stock['pct_chg']:.2f}%")
            report.append(f"   换手率: {stock['turnover_rate']:.2f}% | 评分: {stock['score']:.0f}")
            report.append(f"   买入信号: {stock['buy_signal']}")
            report.append(f"   入场点: {stock['entry_point']}")
            if stock['signals']:
                report.append(f"   技术信号: {', '.join(stock['signals'])}")
    else:
        report.append("\n   暂无符合条件的超短线标的")

    report.append(f"\n📊 短线推荐 (3-7天) - 共{len(short)}只")
    report.append("-" * 40)
    if short:
        for i, stock in enumerate(short, 1):
            report.append(f"\n{i}. {stock['name']} ({stock['ts_code']})")
            report.append(f"   当前价: {stock['close']:.2f} | 涨幅: {stock['pct_chg']:.2f}%")
            report.append(f"   换手率: {stock['turnover_rate']:.2f}% | 评分: {stock['score']:.0f}")
            report.append(f"   买入信号: {stock['buy_signal']}")
            report.append(f"   入场点: {stock['entry_point']}")
    else:
        report.append("\n   暂无符合条件的短线标的")

    report.append("\n" + "=" * 60)
    report.append("⚠️ 风险提示")
    report.append("-" * 40)
    report.append("1. 本系统仅供参考，不构成投资建议")
    report.append("2. 入场前请务必做好风险评估")
    report.append("3. 建议仓位不超过30%，设置止盈止损")
    report.append("4. 市场有风险，投资需谨慎")
    report.append("=" * 60)

    return "\n".join(report)


def run_daily_selection():
    """每日选股运行入口"""
    print("开始每日选股...")
    stocks = get_stock_basic()
    if len(stocks) < 20:
        stocks = get_stock_basic()

    stock_list = stocks.to_dict('records')
    print(f"关注股票数量: {len(stock_list)}")

    market_sentiment = get_market_sentiment()
    print(f"市场情绪: {market_sentiment.get('sentiment', 'neutral')}")

    ultra_short = select_ultra_short_stocks(stocks, market_sentiment, CONFIG['ultra_short_count'])
    print(f"超短线推荐: {len(ultra_short)}只")

    short = select_short_stocks(stocks, market_sentiment, CONFIG['short_count'])
    print(f"短线推荐: {len(short)}只")

    report = generate_recommendation_report(ultra_short, short, market_sentiment)
    return report, ultra_short, short

if __name__ == "__main__":
    report, ultra_short, short = run_daily_selection()
    print("\n" + report)
