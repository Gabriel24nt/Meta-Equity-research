import io
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="META Equity Research",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#10243A"
BLUE = "#2878B5"

st.markdown("""
<style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    div[data-testid="stMetric"] {
        background: rgba(120, 140, 160, 0.08);
        border: 1px solid rgba(120, 140, 160, 0.18);
        padding: 14px 16px;
        border-radius: 10px;
    }
    .small-note {font-size: 0.82rem; color: #7b8794;}
</style>
""", unsafe_allow_html=True)

st.title("META | Equity Research Terminal")
st.caption("Financial analysis • Forecasting • DCF valuation • Trading comparables")
st.info(
    "Educational research project. Market data is retrieved from Yahoo Finance via yfinance "
    "and may be delayed, incomplete or unavailable. Verify all figures against Meta's SEC filings "
    "before using this analysis professionally."
)

@st.cache_data(ttl=3600, show_spinner=False)
def load_company_data(ticker_symbol: str):
    ticker = yf.Ticker(ticker_symbol)
    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        pass
    try:
        hist = ticker.history(period="5y", interval="1d", auto_adjust=False)
    except Exception:
        hist = pd.DataFrame()
    try:
        income = ticker.income_stmt
    except Exception:
        income = pd.DataFrame()
    try:
        balance = ticker.balance_sheet
    except Exception:
        balance = pd.DataFrame()
    try:
        cashflow = ticker.cashflow
    except Exception:
        cashflow = pd.DataFrame()
    return info, hist, income, balance, cashflow

def first_value(df, possible_names, default=np.nan):
    if df is None or df.empty:
        return default
    for name in possible_names:
        if name in df.index:
            vals = df.loc[name].dropna()
            if not vals.empty:
                return float(vals.iloc[0])
    return default

def money(value, currency="USD", decimals=2):
    if pd.isna(value):
        return "N/A"
    if abs(value) >= 1e12:
        return f"{currency} {value/1e12:,.{decimals}f}T"
    if abs(value) >= 1e9:
        return f"{currency} {value/1e9:,.{decimals}f}B"
    if abs(value) >= 1e6:
        return f"{currency} {value/1e6:,.{decimals}f}M"
    return f"{currency} {value:,.{decimals}f}"

def safe_float(value, fallback):
    try:
        result = float(value)
        return result if np.isfinite(result) else fallback
    except (TypeError, ValueError):
        return fallback

def build_dcf(revenue, operating_margin, tax_rate, da_pct, capex_pct, nwc_pct,
              revenue_growth, wacc, terminal_growth, net_cash, shares):
    years = np.arange(1, 6)
    rows = []
    prior_revenue = revenue
    pv_fcf = 0.0
    for year in years:
        forecast_revenue = prior_revenue * (1 + revenue_growth)
        ebit = forecast_revenue * operating_margin
        taxes = max(ebit, 0) * tax_rate
        da = forecast_revenue * da_pct
        capex = forecast_revenue * capex_pct
        change_nwc = (forecast_revenue - prior_revenue) * nwc_pct
        fcf = ebit - taxes + da - capex - change_nwc
        discount_factor = 1 / ((1 + wacc) ** year)
        pv = fcf * discount_factor
        pv_fcf += pv
        rows.append({
            "Year": f"Year {year}",
            "Revenue": forecast_revenue,
            "EBIT": ebit,
            "Taxes": taxes,
            "D&A": da,
            "CapEx": capex,
            "Change in NWC": change_nwc,
            "FCF": fcf,
            "Discount Factor": discount_factor,
            "PV of FCF": pv,
        })
        prior_revenue = forecast_revenue

    final_fcf = rows[-1]["FCF"]
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** 5)
    enterprise_value = pv_fcf + pv_terminal
    equity_value = enterprise_value + net_cash
    per_share = equity_value / shares if shares and shares > 0 else np.nan
    return pd.DataFrame(rows), {
        "PV of forecast FCF": pv_fcf,
        "Terminal Value": terminal_value,
        "PV of Terminal Value": pv_terminal,
        "Enterprise Value": enterprise_value,
        "Net Cash / (Debt)": net_cash,
        "Equity Value": equity_value,
        "Diluted Shares (bn)": shares,
        "Implied Share Price": per_share,
    }

with st.sidebar:
    st.header("Research settings")
    ticker_symbol = st.text_input("Company ticker", "META").strip().upper() or "META"
    st.caption("Default company: Meta Platforms, Inc.")
    if st.button("Refresh market data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Model assumptions are editable and are not company guidance.")

with st.spinner(f"Loading {ticker_symbol} data..."):
    try:
        info, hist, income, balance, cashflow = load_company_data(ticker_symbol)
    except Exception as exc:
        st.error(f"Unable to retrieve market data: {exc}")
        st.stop()

currency = info.get("currency", "USD")
company_name = info.get("longName") or info.get("shortName") or ticker_symbol
current_price = safe_float(info.get("currentPrice"), np.nan)
if pd.isna(current_price) and not hist.empty:
    current_price = safe_float(hist["Close"].dropna().iloc[-1], np.nan)
market_cap = safe_float(info.get("marketCap"), np.nan)
shares = safe_float(info.get("sharesOutstanding"), np.nan) / 1e9
if not np.isfinite(shares) or shares <= 0:
    shares = safe_float(info.get("impliedSharesOutstanding"), np.nan) / 1e9

st.subheader(company_name)
st.caption(f"{ticker_symbol} • {info.get('exchange', 'Exchange unavailable')} • Currency: {currency}")

tab_overview, tab_financials, tab_dcf, tab_comps, tab_thesis = st.tabs([
    "Overview", "Financial Analysis", "DCF Valuation", "Comparable Companies", "Investment Thesis"
])

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Share price", money(current_price, currency))
    c2.metric("Market capitalization", money(market_cap, currency))
    c3.metric("P/E (trailing)", f"{safe_float(info.get('trailingPE'), np.nan):.1f}x" if np.isfinite(safe_float(info.get('trailingPE'), np.nan)) else "N/A")
    c4.metric("52-week range", (
        f"{safe_float(info.get('fiftyTwoWeekLow'), np.nan):.2f} – "
        f"{safe_float(info.get('fiftyTwoWeekHigh'), np.nan):.2f} {currency}"
        if np.isfinite(safe_float(info.get('fiftyTwoWeekLow'), np.nan)) and np.isfinite(safe_float(info.get('fiftyTwoWeekHigh'), np.nan))
        else "N/A"
    ))
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("#### Share price history")
        if not hist.empty:
            chart = hist.reset_index()
            date_col = "Date" if "Date" in chart.columns else chart.columns[0]
            fig = px.line(chart, x=date_col, y="Close", title=f"{ticker_symbol} historical closing price")
            fig.update_layout(height=380, yaxis_title=f"Price ({currency})", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Historical price data is unavailable.")
    with right:
        st.markdown("#### Company profile")
        st.write(info.get("longBusinessSummary", "Company description unavailable."))
        st.markdown(f"**Sector:** {info.get('sector', 'N/A')}")
        st.markdown(f"**Industry:** {info.get('industry', 'N/A')}")
        website = info.get("website")
        if website:
            st.markdown(f"[Company website]({website})")

with tab_financials:
    st.markdown("#### Historical financial statements")
    if income.empty:
        st.warning("Income statement data is unavailable from the selected data provider.")
    else:
        st.markdown("**Income statement (reported values)**")
        st.dataframe(income, use_container_width=True)
        revenue = first_value(income, ["Total Revenue", "Operating Revenue"])
        gross_profit = first_value(income, ["Gross Profit"])
        operating_income = first_value(income, ["Operating Income", "EBIT"])
        net_income = first_value(income, ["Net Income", "Net Income Common Stockholders"])
        cols = st.columns(4)
        cols[0].metric("Latest revenue", money(revenue, currency))
        cols[1].metric("Gross profit", money(gross_profit, currency))
        cols[2].metric("Operating income", money(operating_income, currency))
        cols[3].metric("Net income", money(net_income, currency))
    if not balance.empty:
        st.markdown("**Balance sheet**")
        st.dataframe(balance, use_container_width=True)
    if not cashflow.empty:
        st.markdown("**Cash flow statement**")
        st.dataframe(cashflow, use_container_width=True)

    if not income.empty and "Total Revenue" in income.index:
        rev_series = income.loc["Total Revenue"].dropna().sort_index()
        if len(rev_series) > 1:
            fig = px.bar(x=[str(x.year) if hasattr(x, "year") else str(x) for x in rev_series.index],
                         y=rev_series.values, labels={"x": "Fiscal period", "y": f"Revenue ({currency})"},
                         title="Historical revenue")
            st.plotly_chart(fig, use_container_width=True)

with tab_dcf:
    st.markdown("#### Five-year unlevered DCF model")
    st.caption("The model uses editable assumptions. Confirm historical inputs and source figures before relying on the output.")
    latest_revenue = first_value(income, ["Total Revenue", "Operating Revenue"], 150e9)
    latest_ebit = first_value(income, ["Operating Income", "EBIT"], np.nan)
    default_margin = (latest_ebit / latest_revenue) if np.isfinite(latest_ebit) and latest_revenue else safe_float(info.get("operatingMargins"), 0.35)
    default_margin = float(np.clip(default_margin, 0.05, 0.70))
    cash = first_value(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"], np.nan)
    debt = first_value(balance, ["Total Debt", "Long Term Debt"], 0.0)
    net_cash = (cash - debt) if np.isfinite(cash) else safe_float(info.get("totalCash"), 0) - safe_float(info.get("totalDebt"), 0)
    da_value = first_value(cashflow, ["Depreciation And Amortization", "Depreciation Amortization Depletion"], np.nan)
    capex_value = first_value(cashflow, ["Capital Expenditure", "Capital Expenditures"], np.nan)
    da_pct_default = abs(da_value / latest_revenue) if np.isfinite(da_value) and latest_revenue else 0.08
    capex_pct_default = abs(capex_value / latest_revenue) if np.isfinite(capex_value) and latest_revenue else 0.10

    a, b, c = st.columns(3)
    with a:
        revenue_growth = st.number_input("Annual revenue growth", min_value=-0.20, max_value=0.50, value=0.12, step=0.01, format="%.2f")
        operating_margin = st.number_input("EBIT margin", min_value=0.01, max_value=0.80, value=default_margin, step=0.01, format="%.2f")
    with b:
        tax_rate = st.number_input("Cash tax rate", min_value=0.00, max_value=0.50, value=0.16, step=0.01, format="%.2f")
        wacc = st.number_input("WACC", min_value=0.03, max_value=0.30, value=0.09, step=0.005, format="%.3f")
    with c:
        terminal_growth = st.number_input("Terminal growth", min_value=0.00, max_value=0.08, value=0.025, step=0.005, format="%.3f")
        nwc_pct = st.number_input("Change in NWC / incremental revenue", min_value=-0.20, max_value=0.30, value=0.02, step=0.01, format="%.2f")
    d, e, f = st.columns(3)
    with d:
        da_pct = st.number_input("D&A / revenue", min_value=0.00, max_value=0.30, value=float(np.clip(da_pct_default, 0, 0.30)), step=0.01, format="%.2f")
    with e:
        capex_pct = st.number_input("CapEx / revenue", min_value=0.00, max_value=0.40, value=float(np.clip(capex_pct_default, 0, 0.40)), step=0.01, format="%.2f")
    with f:
        st.metric("Net cash / (debt) used", money(net_cash, currency))
    if wacc <= terminal_growth:
        st.error("WACC must be higher than terminal growth for the Gordon Growth DCF.")
    elif not np.isfinite(latest_revenue) or latest_revenue <= 0:
        st.error("A valid latest revenue figure is required to calculate the DCF.")
    elif not np.isfinite(shares) or shares <= 0:
        st.error("Diluted shares outstanding are unavailable. DCF per-share value cannot be calculated.")
    else:
        forecast, valuation = build_dcf(
            latest_revenue, operating_margin, tax_rate, da_pct, capex_pct,
            nwc_pct, revenue_growth, wacc, terminal_growth, net_cash, shares
        )
        st.dataframe(forecast.style.format({
            "Revenue": "{:,.0f}", "EBIT": "{:,.0f}", "Taxes": "{:,.0f}",
            "D&A": "{:,.0f}", "CapEx": "{:,.0f}", "Change in NWC": "{:,.0f}",
            "FCF": "{:,.0f}", "Discount Factor": "{:.3f}", "PV of FCF": "{:,.0f}"
        }), use_container_width=True)
        x, y, z = st.columns(3)
        x.metric("Enterprise value", money(valuation["Enterprise Value"], currency))
        y.metric("Equity value", money(valuation["Equity Value"], currency))
        z.metric("DCF implied value / share", f"{currency} {valuation['Implied Share Price']:,.2f}")
        if np.isfinite(current_price) and current_price > 0:
            upside = valuation["Implied Share Price"] / current_price - 1
            st.metric("Implied upside / (downside)", f"{upside:+.1%}")
        st.markdown("**Valuation bridge**")
        bridge = pd.DataFrame({"Metric": list(valuation.keys()), "Value": list(valuation.values())})
        st.dataframe(bridge, use_container_width=True)

        # Export the model and available historical statements to an Excel workbook.
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            forecast.to_excel(writer, sheet_name="DCF Forecast", index=False)
            bridge.to_excel(writer, sheet_name="DCF Valuation", index=False)
            if not income.empty:
                income.to_excel(writer, sheet_name="Income Statement")
            if not balance.empty:
                balance.to_excel(writer, sheet_name="Balance Sheet")
            if not cashflow.empty:
                cashflow.to_excel(writer, sheet_name="Cash Flow")
        st.download_button(
            "Download financial model (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"{ticker_symbol}_equity_research_model.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption("This is a simplified DCF. It is not a fully integrated three-statement forecast; assumptions should be justified in the final research report.")

with tab_comps:
    st.markdown("#### Trading comparables")
    st.caption("Illustrative peer set. These companies have different business mixes and are not perfectly comparable.")
    peers = st.multiselect("Peer companies", ["GOOGL", "SNAP", "PINS", "AMZN", "NFLX"], default=["GOOGL", "SNAP", "PINS"])
    rows = []
    for peer in peers:
        try:
            peer_info = yf.Ticker(peer).info or {}
            rows.append({
                "Ticker": peer,
                "Company": peer_info.get("shortName", peer),
                "Market Cap": peer_info.get("marketCap", np.nan),
                "EV / Revenue": peer_info.get("enterpriseToRevenue", np.nan),
                "EV / EBITDA": peer_info.get("enterpriseToEbitda", np.nan),
                "P/E": peer_info.get("trailingPE", np.nan),
                "Revenue Growth": peer_info.get("revenueGrowth", np.nan),
            })
        except Exception:
            rows.append({"Ticker": peer, "Company": peer, "Market Cap": np.nan,
                         "EV / Revenue": np.nan, "EV / EBITDA": np.nan, "P/E": np.nan,
                         "Revenue Growth": np.nan})
    if rows:
        st.dataframe(pd.DataFrame(rows).style.format({
            "Market Cap": lambda x: money(x, currency),
            "EV / Revenue": "{:.2f}x", "EV / EBITDA": "{:.2f}x",
            "P/E": "{:.2f}x", "Revenue Growth": "{:.1%}"
        }), use_container_width=True)
    else:
        st.info("Select at least one peer company.")

with tab_thesis:
    st.markdown("#### Investment research framework")
    st.write("Use this section to develop a documented, evidence-based investment thesis. The template below is intentionally blank: conclusions must follow verified analysis.")
    thesis = st.text_area("Investment thesis", placeholder="Summarize the core investment argument, supported by evidence...", height=140)
    catalysts = st.text_area("Potential catalysts", placeholder="Product launches, advertising trends, AI monetization, margin changes...", height=100)
    risks = st.text_area("Key risks", placeholder="Regulatory, competition, execution, capex, valuation, macroeconomic risks...", height=100)
    rating = st.selectbox("Preliminary stance", ["Not yet rated", "Buy", "Hold", "Sell"])
    st.caption("A rating should only be selected after completing and documenting the analysis.")
    if st.button("Prepare research notes"):
        notes = f"""META EQUITY RESEARCH NOTES
Date: {datetime.now().date()}
Ticker: {ticker_symbol}
Preliminary stance: {rating}

INVESTMENT THESIS
{thesis}

POTENTIAL CATALYSTS
{catalysts}

KEY RISKS
{risks}
"""
        st.download_button("Download research notes", notes, file_name=f"{ticker_symbol}_research_notes.txt")

st.divider()
st.caption("Built as an educational portfolio project by Alan Gabriel Nte • Data provider: Yahoo Finance (via yfinance) • Always verify figures against company filings.")
