# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is a Chinese mutual fund valuation web application with the following architecture:

```
web/
├── fund-estimator-web/          # Main Flask web application
│   ├── app.py                   # Flask web server (main entry point)
│   ├── app_optimized.py         # Optimized version of Flask app
│   ├── fund_estimator.py        # Core valuation logic and market analysis
│   ├── fund_api.py              # API adapter layer for web interface
│   ├── fund_api_optimized.py    # Optimized API adapter
│   ├── templates/index.html     # Frontend HTML interface
│   ├── api/index.py            # Vercel serverless API endpoint
│   ├── requirements.txt         # Python dependencies
│   ├── Procfile                # Heroku/Render deployment config
│   └── vercel.json             # Vercel deployment config
└── fund_holdings/               # CSV data files with fund holdings
    ├── 007455.csv              # Individual fund holding data
    ├── 012922.csv              # (6-digit fund codes)
    └── 016531.csv
```

## Common Commands

### Development
```bash
# Install dependencies
pip install -r fund-estimator-web/requirements.txt

# Run development server
cd fund-estimator-web
python app.py

# Run optimized version
python app_optimized.py
```

### Deployment Commands
```bash
# Production server with Gunicorn
cd fund-estimator-web
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Background deployment
nohup python app.py &
```

## Core Architecture

### Data Flow
1. **fund_holdings/ CSV files** → Raw fund portfolio data (6-digit fund codes)
2. **fund_estimator.py** → Core valuation engine with market timing logic
3. **fund_api.py** → API adapter layer that wraps estimator for web use
4. **app.py** → Flask web server with caching and REST endpoints
5. **templates/index.html** → Responsive mobile-first frontend

### Key Components

**fund_estimator.py** - Core valuation logic:
- `determine_calculation_mode()` - Global market timing logic (CURRENT_DAY vs PREVIOUS_DAY)
- `get_stock_price_changes()` - Multi-market stock price fetching
- `smart_ticker_converter()` - Converts Chinese stock codes to yfinance tickers
- Global market support: A-shares (.SS/.SZ), Hong Kong (.HK), US markets

**fund_api.py** - API adapter:
- `calculate_fund_estimate_api()` - JSON-structured valuation results
- `get_fund_summary_info()` - Fund metadata and statistics

**app.py** - Web server:
- Caching system (5-minute duration)
- REST API endpoints: `/api/funds`, `/api/estimate`
- Real-time vs. historical valuation modes

### Market Logic
The application intelligently switches between real-time and historical modes based on global market hours:
- **Real-time mode**: During active trading hours (any global market)
- **Historical mode**: During global market closure (Beijing 05:00-09:30, weekends)

## Fund Data Format

CSV files in `fund_holdings/` must contain:
- `公司名称` (Company Name)
- `证券代码` (Stock Code) 
- `占基金资产净值比例(%)` (Portfolio Weight %)

## Deployment Platforms

Configured for multiple platforms:
- **Vercel**: Serverless deployment via `api/index.py` and `vercel.json`
- **Render/Heroku**: Traditional server via `Procfile`
- **Local**: Direct Flask development server

## Dependencies

Key Python packages:
- Flask 2.3.3 + Flask-CORS - Web framework
- pandas 2.1.0 - Data processing
- yfinance 0.2.18 - Stock price data
- pytz 2023.3 - Timezone handling
- gunicorn 21.2.0 - Production WSGI server