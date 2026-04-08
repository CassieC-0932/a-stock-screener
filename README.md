# A-Share Stock Screener

A comprehensive A-share stock screening system that combines technical analysis, fundamental analysis, and market sentiment analysis to identify potential investment opportunities.

## Features

- **Multi-dimensional analysis**: Combines technical, fundamental, and news sentiment analysis
- **Dual strategy**: Ultra-short term (1-3 days) and short term (3-7 days)
- **Comprehensive scoring**: 100-point system evaluating multiple factors
- **Real-time data**: Uses Eastmoney and Tencent APIs for up-to-date market data
- **Risk management**: Built-in risk assessment and position sizing recommendations

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure the system: Copy `config.example.py` to `config.py` and add your Tushare API token
4. Run the system: `python scripts/run_daily.py`

## Usage

### Daily Screening

```bash
python scripts/run_daily.py
```

### Auction Analysis

```bash
python scripts/run_auction.py
```

### Backtesting

```bash
python scripts/backtest.py
```

### Analysis

```bash
python scripts/analyze.py
```

## Documentation

- [Strategy Guide](references/strategy.md)
- [Data Sources](references/data-sources.md)
- [Installation Guide](references/installation.md)

## Risk Disclaimer

This system is for informational purposes only and does not constitute investment advice. Always perform your own research before making investment decisions.

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
