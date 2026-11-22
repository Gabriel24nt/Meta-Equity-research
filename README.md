# META Equity Research

**Financial Analysis | Financial Modeling | DCF Valuation | Trading Comparables**

A Python and Streamlit research terminal for an educational equity research project on Meta Platforms, Inc. (NASDAQ: META).

## Features

- Company overview and historical share-price chart
- Historical income statement, balance sheet and cash-flow statement (when available from the data provider)
- Key market metrics
- Editable five-year simplified DCF model
- Illustrative trading-comparables table
- Investment thesis and research-notes template

## Run locally

1. Install Python 3.10 or later.
2. Clone or download this repository.
3. Create and activate a virtual environment.
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the application:
   ```bash
   streamlit run app.py
   ```

## Important data and methodology notes

- Market and financial data are retrieved from Yahoo Finance through `yfinance`. This is a convenient data source for a student project, not a substitute for official filings.
- Verify reported financial figures against Meta's annual reports, quarterly reports and SEC filings before using them in a research report.
- The DCF is a simplified unlevered free-cash-flow model. It uses editable assumptions and is not a fully integrated three-statement forecast.
- Comparable companies are illustrative. Explain differences in business mix, growth, margins and capital intensity before drawing conclusions.
- Do not treat the generated valuation as investment advice or a professional investment recommendation.

## Suggested project extensions

- Build a fully integrated three-statement model.
- Add historical financial-ratio analysis and common-size statements.
- Add DCF sensitivity tables for WACC and terminal growth.
- Add precedent transactions analysis.
- Export model outputs to Excel.
- Add a documented investment-research report with cited sources.

## Author

**Alan Gabriel Nte**  
Burgundy School of Business — Master in Management  
[LinkedIn](https://www.linkedin.com/in/alan-gabriel-nte-77b510388/) | [GitHub](https://github.com/Gabriel24nt)
