# Installation Guide for A-Share Stock Screener

## Prerequisites

- Python 3.7+ 
- pip package manager
- Tushare API token (optional, for advanced features)

## Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/a-stock-screener.git
   cd a-stock-screener
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**
   - Copy `config.example.py` to `config.py`
   - Add your Tushare API token (optional)
   - Adjust screening parameters as needed

4. **Test the installation**
   ```bash
   python scripts/run_daily.py
   ```

## Dependencies

- pandas: Data manipulation
- numpy: Numerical calculations
- requests: API communication
- tushare: Financial data (optional)
- matplotlib: Data visualization (optional)

## System Requirements

- CPU: 2-core or higher
- Memory: 4GB or higher
- Storage: 1GB free space
- Internet connection: Required for data collection

## Troubleshooting

1. **API connection issues**
   - Check your internet connection
   - Verify API keys are correct
   - Check API rate limits

2. **Data errors**
   - Clear the cache directory
   - Update the data sources
   - Check for API changes

3. **Performance issues**
   - Reduce the number of stocks analyzed
   - Optimize screening parameters
   - Use a faster internet connection

## Updates

To update the system:
```bash
git pull
pip install -r requirements.txt
```

## Support

For issues and feature requests, please open an issue on GitHub.
