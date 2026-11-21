import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import datetime

from calendar_news import get_market_status, get_high_impact_news
from strategy import run_smc_ict_backtest
from instruments import INSTRUMENT_CATEGORIES, generate_option_chain_strikes

# 1. Page Config & TradingView Pro Dark Theme
st.set_page_config(
    page_title="SMC & ICT F&O Algo Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #E6EDF3; }
    [data-testid="stSidebar"] { background-color: #161B22; }
    .metric-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .metric-title { font-size: 13px; color: #8B949E; }
    .metric-value { font-size: 22px; font-weight: bold; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# 2. Header & Holiday Calendar
col_title, col_status = st.columns([3, 1.5])
with col_title:
    st.title("⚡ SMC & ICT F&O Algo Dashboard")
with col_status:
    selected_cal_date = st.date_input("📅 மார்க்கெட் கேலண்டர் செக்", datetime.date.today())
    is_open, status_msg = get_market_status(selected_cal_date)
    if is_open:
        st.success(status_msg)
    else:
        st.error(status_msg)

# 3. Sidebar: Order-Wise Market Selection
st.sidebar.header("📌 Step 1: மார்க்கெட் & F&O தேர்வு")

data_source = st.sidebar.radio(
    "டேட்டா சோர்ஸ்:",
    ["📡 Live Chart (F&O Indices & Stocks)", "📂 CSV File Upload (Backtest)"]
)

df = pd.DataFrame()
market_type = "Indian"
selected_name = "Custom CSV"
lot_size = 75
strike_step = 50
segment = "Spot / Equity"
lots_count = 1

if data_source == "📡 Live Chart (F&O Indices & Stocks)":
    # வரிசையாக 1 -> 2 -> 3 தேர்வு
    category = st.sidebar.selectbox("1️⃣ பிரிவு (Category):", list(INSTRUMENT_CATEGORIES.keys()))
    instruments_dict = INSTRUMENT_CATEGORIES[category]

    instrument_list = list(instruments_dict.keys()) + ["➕ வேறு NSE F&O ஸ்டாக் டைப் செய்..."]
    chosen_item = st.sidebar.selectbox("2️⃣ இன்ஸ்ட்ருமென்ட் (Index / Stock):", instrument_list)

    if chosen_item == "➕ வேறு NSE F&O ஸ்டாக் டைப் செய்...":
        custom_sym = st.sidebar.text_input("NSE Symbol டைப் செய்க (உ-ம்: MARUTI, SUNPHARMA):", "MARUTI").upper().strip()
        ticker = f"{custom_sym}.NS" if not custom_sym.endswith(".NS") else custom_sym
        selected_name = custom_sym
        lot_size = st.sidebar.number_input("Lot Size:", 1, 5000, 100)
        strike_step = st.sidebar.number_input("Strike Step:", 1, 500, 50)
        market_type = "Indian"
    else:
        info = instruments_dict[chosen_item]
        ticker = info["symbol"]
        selected_name = chosen_item
        lot_size = info["lot_size"]
        strike_step = info["strike_step"]
        market_type = info["market"]

    # Segment Selection (Spot / Futures / Options)
    segment = st.sidebar.radio(
        "3️⃣ டிரேடிங் வகை (Segment):",
        ["Spot Chart", "Futures (F&O)", "Option Chain (CE / PE)"]
    )
    lots_count = st.sidebar.number_input(f"எத்தனை Lot? (1 Lot = {lot_size} Qty):", 1, 50, 1)

    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ சார்ட் டைம்ஃப்ரேம்")
    interval = st.sidebar.selectbox("Timeframe:", ["5m", "15m", "1m", "1h"], index=0)
    period = st.sidebar.selectbox("கால அளவு:", ["5d", "1mo", "1d"], index=0)

    if st.sidebar.button("🔄 லைவ் சார்ட் ரெஃப்ரெஷ்"):
        st.cache_data.clear()

    @st.cache_data(ttl=60)
    def load_live_data(sym, per, intv):
        raw = yf.download(sym, period=per, interval=intv, progress=False)
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.reset_index()
        dt_col = "Datetime" if "Datetime" in raw.columns else "Date"
        raw.rename(columns={dt_col: "Datetime"}, inplace=True)
        raw["Datetime"] = pd.to_datetime(raw["Datetime"])
        if raw["Datetime"].dt.tz is not None:
            raw["Datetime"] = raw["Datetime"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
        return raw[["Datetime", "Open", "High", "Low", "Close"]].dropna()

    with st.spinner(f"{selected_name} சார்ட் லோட் ஆகிறது..."):
        df = load_live_data(ticker, period, interval)

else:
    uploaded_file = st.sidebar.file_uploader("1m / 5m CSV ஃபைலை அப்லோட் செய்யவும்", type=["csv"])
    if uploaded_file is not None:
        raw = pd.read_csv(uploaded_file)
        col_map = {}
        for c in raw.columns:
            cl = c.strip().lower()
            if cl in ["datetime", "date", "time", "timestamp"]:
                col_map[c] = "Datetime"
            elif cl == "open":
                col_map[c] = "Open"
            elif cl == "high":
                col_map[c] = "High"
            elif cl == "low":
                col_map[c] = "Low"
            elif cl == "close":
                col_map[c] = "Close"
        raw.rename(columns=col_map, inplace=True)
        if all(k in raw.columns for k in ["Datetime", "Open", "High", "Low", "Close"]):
            raw["Datetime"] = pd.to_datetime(raw["Datetime"])
            df = raw[["Datetime", "Open", "High", "Low", "Close"]].dropna().tail(1500)
        else:
            st.error("CSV ஃபைலில் Datetime, Open, High, Low, Close காலம்கள் இருக்க வேண்டும்.")

# Step 2: SMC & ICT Controls
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Step 2: SMC & ICT செட்டிங்ஸ்")
swing_len = st.sidebar.slider("Liquidity Swing Length", 2, 10, 3)
rr_ratio = st.sidebar.slider("Risk : Reward Ratio (1 : X)", 1.0, 5.0, 2.0, 0.5)
use_killzone = st.sidebar.checkbox("Kill Zone நேரத்தில் மட்டும் டிரேட் எடு", value=False)
brokerage_pts = st.sidebar.number_input("Brokerage & Slippage (Points)", 0.0, 20.0, 1.0, 0.5)
show_fvg = st.sidebar.checkbox("FVG பாக்ஸ் காட்டு", value=True)
show_ob = st.sidebar.checkbox("Order Block காட்டு", value=True)

# 4. Main Dashboard Rendering
if not df.empty:
    current_price = float(df["Close"].iloc[-1])
    total_qty = lot_size * lots_count

    trades_df, fvgs, order_blocks, liq_levels = run_smc_ict_backtest(
        df,
        swing_len=swing_len,
        rr_ratio=rr_ratio,
        use_killzone=use_killzone,
        market_type=market_type,
        brokerage_pts=brokerage_pts
    )

    total_trades = len(trades_df)
    wins = len(trades_df[trades_df["Result"] == "PROFIT ✅"]) if total_trades > 0 else 0
    losses = len(trades_df[trades_df["Result"] == "LOSS ❌"]) if total_trades > 0 else 0
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    net_pnl_pts = trades_df["PnL (Pts)"].sum() if total_trades > 0 else 0.0
    est_rupees_pnl = net_pnl_pts * total_qty

    # Top Info Bar
    st.markdown(f"### 📌 தேர்ந்தெடுக்கப்பட்டது: **{selected_name}** | வகை: **{segment}** | தற்போதைய விலை: **₹{current_price:,.2f}** | Qty: **{total_qty} ({lots_count} Lot)**")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>மொத்த டிரேடுகள்</div><div class='metric-value'>{total_trades}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>Win Rate %</div><div class='metric-value' style='color:#00E5FF;'>{win_rate:.1f}%</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>Win / Loss</div><div class='metric-value'><span style='color:#00C853;'>{wins}W</span> / <span style='color:#FF1744;'>{losses}L</span></div></div>", unsafe_allow_html=True)
    pnl_color = "#00C853" if net_pnl_pts >= 0 else "#FF1744"
    c4.markdown(f"<div class='metric-card'><div class='metric-title'>நிகர பாயிண்ட்ஸ்</div><div class='metric-value' style='color:{pnl_color};'>{net_pnl_pts:+.2f}</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='metric-card'><div class='metric-title'>மதிப்பிடப்பட்ட P&L ({lots_count} Lot)</div><div class='metric-value' style='color:{pnl_color};'>₹{est_rupees_pnl:+,.0f}</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart + Right Panel (Option Chain / News Tabs)
    chart_col, side_col = st.columns([3, 1.2])

    with chart_col:
        st.subheader(f"📊 {selected_name} ({segment}) - SMC & ICT Chart")
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df["Datetime"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            increasing_line_color="#00C853", decreasing_line_color="#FF1744", name="Price"
        ))

        if show_fvg:
            for fvg in fvgs:
                color = "rgba(0, 200, 83, 0.18)" if "Bullish" in fvg["type"] else "rgba(255, 23, 68, 0.18)"
                fig.add_shape(
                    type="rect", x0=fvg["start"], x1=df["Datetime"].iloc[-1],
                    y0=fvg["bottom"], y1=fvg["top"], fillcolor=color, line=dict(width=0)
                )

        if show_ob:
            for ob in order_blocks:
                border_col = "#FFD600" if "Bullish" in ob["type"] else "#00E5FF"
                fig.add_shape(
                    type="rect", x0=ob["time"], x1=df["Datetime"].iloc[-1],
                    y0=ob["low"], y1=ob["high"],
                    fillcolor="rgba(255, 214, 0, 0.08)", line=dict(color=border_col, width=1, dash="dot")
                )

        if total_trades > 0:
            buys = trades_df[trades_df["Type"] == "BUY"]
            sells = trades_df[trades_df["Type"] == "SELL"]
            if not buys.empty:
                fig.add_trace(go.Scatter(
                    x=buys["Entry Time"], y=buys["Entry Price"], mode="markers", name="BUY (CE / Long)",
                    marker=dict(symbol="triangle-up", size=12, color="#00C853", line=dict(width=1, color="white"))
                ))
            if not sells.empty:
                fig.add_trace(go.Scatter(
                    x=sells["Entry Time"], y=sells["Entry Price"], mode="markers", name="SELL (PE / Short)",
                    marker=dict(symbol="triangle-down", size=12, color="#FF1744", line=dict(width=1, color="white"))
                ))

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
            height=580, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with side_col:
        tab_oc, tab_news = st.tabs(["⛓️ Option Chain", "📰 Live News"])

        with tab_oc:
            atm_strike, strikes_list = generate_option_chain_strikes(current_price, strike_step)
            st.info(f"**ATM Strike:** {atm_strike} | **Lot Size:** {lot_size}")
            st.caption("BUY சிக்னல் -> ATM/ITM **CE** | SELL சிக்னல் -> ATM/ITM **PE**")
            st.dataframe(pd.DataFrame(strikes_list), use_container_width=True, hide_index=True, height=400)
            st.caption("💡 லைவ் Option பிரீமியம் & Futures டேட்டாவிற்கு அடுத்து Dhan / Angel One API இணைக்கலாம்.")

        with tab_news:
            news_list = get_high_impact_news()
            if news_list:
                for n in news_list:
                    st.markdown(f"**{n['impact']}** [{n['title']}]({n['link']})")
                    st.caption(f"🕒 {n['published']}")
                    st.markdown("---")
            else:
                st.info("தற்போது முக்கிய செய்திகள் எதுவும் இல்லை.")

    # Auto Trade Journal
    st.subheader("📝 Auto Trade Journal (ஒவ்வொரு டிரேடின் முழுக் காரணம்)")
    if total_trades > 0:
        # Option Strike Suggestion சேர்த்தல்
        trades_df["Suggested Option"] = trades_df.apply(
            lambda r: f"{int(round(r['Entry Price']/strike_step)*strike_step)} {'CE' if r['Type']=='BUY' else 'PE'}",
            axis=1
        )
        display_cols = [
            "Entry Time", "Type", "Suggested Option", "Entry Price", "SL", "Target",
            "Exit Price", "PnL (Pts)", "Result", "Entry Reason", "In-Trade Story", "Exit Reason"
        ]
        st.dataframe(trades_df[display_cols], use_container_width=True, height=350)

        csv_export = trades_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"⬇️ {selected_name} பேக்டெஸ்ட் ரிப்போர்ட் டவுன்லோட் (CSV)",
            data=csv_export,
            file_name=f"{selected_name}_smc_ict_report.csv",
            mime="text/csv"
        )
    else:
        st.warning("இந்த செட்டிங்ஸில் டிரேட் கிடைக்கவில்லை. சைட்பாரில் 'Kill Zone' ஆஃப் செய்து அல்லது Swing Length மாற்றிப் பாருங்கள்.")
else:
    st.error("டேட்டா லோட் ஆகவில்லை. இன்டர்நெட் அல்லது ஸ்டாக் சிம்பலைச் சரிபார்க்கவும்.")
  
