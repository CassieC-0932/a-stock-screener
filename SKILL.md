---
name: a-stock-screener
description: A comprehensive A-share stock screening system that combines technical analysis, fundamental analysis, and market sentiment analysis to identify potential investment opportunities. Use when you need to select stocks based on multiple criteria including price trends, volume analysis, moving averages, and market conditions.
---

# A-Share Stock Screener

## Overview

This skill provides a complete A-share stock screening system that combines technical analysis, fundamental analysis, and market sentiment analysis to identify potential investment opportunities. The system includes both ultra-short term (1-3 days) and short term (3-7 days) strategies with a comprehensive scoring system.

## Key Features

- **Multi-dimensional analysis**: Combines technical, fundamental, and news sentiment analysis
- **Dual strategy**: Ultra-short term (1-3 days) and short term (3-7 days)
- **Comprehensive scoring**: 100-point system evaluating multiple factors
- **Real-time data**: Uses Eastmoney and Tencent APIs for up-to-date market data
- **Risk management**: Built-in risk assessment and position sizing recommendations

## Usage

### Basic Screening

To run the daily stock screening:
```bash
python scripts/run_daily.py
```

### Auction Analysis

For pre-market auction analysis (9:15-9:25):
```bash
python scripts/run_auction.py
```

### Backtesting

To backtest the strategy against historical data:
```bash
python scripts/backtest.py
```

### Analysis

To analyze the results of a screening:
```bash
python scripts/analyze.py
```

## Configuration

The system can be configured through `config.py` with the following parameters:

- Tushare token for advanced data access
- Focus industries
- Screening parameters for ultra-short and short term strategies
- Risk management settings

## Data Sources

- **Eastmoney API**: For real-time stock data
- **Tushare API**: For fundamental data (requires token)
- **Tencent API**: For historical K-line data

## Output

The system generates:
- Daily screening reports in text and JSON format
- Auction analysis reports
- Backtesting results
- Detailed stock analysis with scoring and recommendations

## Risk Disclaimer

This system is for informational purposes only and does not constitute investment advice. Always perform your own research before making investment decisions.

## Technical Details

The screening process involves:
1. Basic filtering (excluding ST stocks,科创板, etc.)
2. Technical analysis (moving averages, MACD, volume analysis)
3. Fundamental analysis (market cap, valuation metrics)
4. Sentiment analysis (news and market trends)
5. Comprehensive scoring and ranking

For detailed implementation, refer to the scripts in the `scripts/` directory.
