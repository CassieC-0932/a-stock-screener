---
name: a-stock-screener
description: >
  A-share (A股) intelligent stock screening system with technical analysis, fundamental analysis,
  auction analysis, and backtesting. Combines MA/MACD/KDJ/RSI/Bollinger indicators with growth
  stock identification, volume analysis, and multi-factor scoring. Supports ultra-short (1-3 days)
  and short-term (3-7 days) strategies. Data sources: Eastmoney, Sina, Tencent APIs.
  Use when: user needs to screen/select Chinese A-share stocks (选股/筛选股票), run daily stock
  screening (每日选股), analyze auction data (竞价分析), backtest strategies (回测), or build
  stock recommendation systems. Triggers on: 选股, 股票筛选, A股, 选股系统, stock screener,
  stock screening, daily selection, auction analysis.
---

# A-Share Stock Screener 🦞

Multi-factor quantitative stock screening system for Chinese A-shares.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure
cp config.example.py scripts/config.py
# Edit scripts/config.py: set TUSHARE_TOKEN if available

# Run daily screening (Eastmoney source)
python scripts/run_daily.py

# Or use Sina source (more stable during early trading)
python scripts/run_daily_sina.py

# Pre-market auction analysis (9:15-9:25)
python scripts/run_auction.py

# Backtest
python scripts/backtest.py

# Review results
python scripts/analyze.py
```

## Architecture

```
scripts/
├── data_fetcher.py          # Data layer: Eastmoney + Sina + Tencent APIs
├── stock_filter.py          # Core screening: growth stock + 3 optimization conditions
├── technical_analysis.py    # Indicators: MA/MACD/KDJ/RSI/Bollinger/Volume
├── fundamental_analysis.py  # Basics: market cap, valuation, turnover
├── news_analysis.py         # Sentiment: market mood, sector heat
├── auction_analysis.py      # Pre-market: call auction scoring
├── recommender.py           # Engine: multi-factor scoring + report generation
├── run_daily.py             # Entry: daily screening (Eastmoney)
├── run_daily_sina.py        # Entry: daily screening (Sina)
├── run_auction.py           # Entry: auction analysis
├── backtest.py              # Strategy backtesting
├── analyze.py               # Post-market review
└── config.py                # Configuration (copy from config.example.py)
```

## Screening Logic

### Core Strategy: Low-Position Growth Stocks

**Base condition** (5pts): Price above MA10 or MA alignment trending up.

**Optimization conditions** (additive scoring):
- MACD bullish divergence (+5pts): Price at 20-day low but MACD not
- Volume contraction pullback (+3pts): Vol < 80% of 5-day avg + price down
- Oversold bounce (+3pts): 3 consecutive down days after prior uptrend

**Growth signals**:
- Low position + MA uptrend (+5pts): price within 10% of MA60
- Near 60-day low (+3pts)
- MA20 support (+2pts)
- Small positive candles × 2+ (+3pts): daily gains 0-3%
- MACD golden cross (+3pts)
- Consecutive up days (+2pts)
- Moderate volume (0.8-1.5x avg) (+2pts)

**Total score**: 5-25pts, sorted descending. Top 15 reported.

### Filters Applied
- Exclude: ST, *ST, BJ (北交所), 688 (科创板)
- Price < ¥25
- Not at daily limit up
- Circulating market cap: 30-500亿 (expand to 20-800亿 if <10 results)

### Risk Warnings
- Volume spike (>2x), far from MA20 (>15%), high position (>30% above MA60)

### Auction Analysis (9:15-9:25)
Scores based on: opening change %, volume ratio, bid/ask ratio.
Advice levels: 强烈买入 / 建议买入 / 观望 / 放弃.

### Recommender Engine (alternative entry)
100-point system: Technical 40 + Fundamental 30 + News 20 + Sentiment 10.
Ultra-short (1-3d): 2-8% gain, turnover ≥3%, score ≥25.
Short (3-7d): score ≥20.

## Data Sources

| Source | Use Case | Stability |
|--------|----------|-----------|
| Eastmoney push2 API | Full market quotes, K-line | Primary, may timeout |
| Sina Market Center | Full market quotes | Backup, good for early trading |
| Tencent ifzq API | Historical K-line (复权) | Stable |
| Eastmoney kline API | Daily K-line | Primary |

## Configuration

Key params in `config.py`:
- `focus_industries`: Sector preferences
- `ultra_short` / `short`: Strategy thresholds
- `risk_control`: Position limits, stop-loss/take-profit
- `TUSHARE_TOKEN`: Optional, for advanced fundamental data

## Output

Reports saved to `scripts/reports/`:
- `{date}.txt`: Human-readable screening report
- `{date}.json`: Machine-readable results with all fields
- `auction_{date}.json`: Auction analysis results

## Notes

- All data fetched via public APIs, no authentication required for basic usage
- Rate limiting: add `time.sleep(0.1)` between batch requests
- Early trading (before 9:30): Sina source returns `settlement` (昨收) as fallback
- Tushare token is optional; system works without it using free API sources
