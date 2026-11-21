import pandas as pd
import numpy as np


def is_in_killzone(ts, market_type="Indian"):
    """Kill Zone நேரத்திற்குள் இருக்கிறதா எனச் சரிபார்க்கும்."""
    hour = ts.hour
    minute = ts.minute
    time_val = hour * 60 + minute

    if market_type == "Indian":
        # Morning: 09:15 - 10:45 IST | Afternoon: 13:30 - 14:45 IST
        return (555 <= time_val <= 645) or (810 <= time_val <= 885)
    else:
        # London: 12:30 - 15:30 IST | New York: 17:30 - 20:30 IST
        return (750 <= time_val <= 930) or (1050 <= time_val <= 1230)


def run_smc_ict_backtest(
    df,
    swing_len=3,
    rr_ratio=2.0,
    use_killzone=False,
    market_type="Indian",
    brokerage_pts=1.0
):
    """
    SMC + ICT Unlimited Backtest Engine.
    ஒவ்வொரு டிரேடிற்கும் Entry Reason, In-Trade Story (MAE/MFE), Exit Reason உருவாக்கும்.
    """
    data = df.copy().reset_index(drop=True)
    if len(data) < 20:
        return pd.DataFrame(), [], [], []

    # 1. Swing High (BSL) & Swing Low (SSL) கண்டுபிடித்தல்
    data["swing_high"] = np.nan
    data["swing_low"] = np.nan

    for i in range(swing_len, len(data) - swing_len):
        window_high = data["High"].iloc[i - swing_len : i + swing_len + 1]
        window_low = data["Low"].iloc[i - swing_len : i + swing_len + 1]
        if data["High"].iloc[i] == window_high.max():
            data.loc[i, "swing_high"] = data["High"].iloc[i]
        if data["Low"].iloc[i] == window_low.min():
            data.loc[i, "swing_low"] = data["Low"].iloc[i]

    # 2. FVG (Fair Value Gap) & Order Block கண்டுபிடித்தல்
    fvgs = []
    order_blocks = []
    liquidity_levels = []
    trades = []

    last_swing_high = None
    last_swing_low = None
    in_trade = False
    active_trade = None

    for i in range(3, len(data)):
        row = data.iloc[i]
        ts = row["Datetime"]

        # முந்தைய Swing High / Low அப்டேட் செய்தல்
        if not np.isnan(data["swing_high"].iloc[i - swing_len]):
            last_swing_high = data["swing_high"].iloc[i - swing_len]
            liquidity_levels.append({
                "type": "BSL", "price": last_swing_high, "time": data["Datetime"].iloc[i - swing_len]
            })
        if not np.isnan(data["swing_low"].iloc[i - swing_len]):
            last_swing_low = data["swing_low"].iloc[i - swing_len]
            liquidity_levels.append({
                "type": "SSL", "price": last_swing_low, "time": data["Datetime"].iloc[i - swing_len]
            })

        # FVG செக் (3-Candle Pattern)
        bull_fvg = data["Low"].iloc[i] > data["High"].iloc[i - 2]
        bear_fvg = data["High"].iloc[i] < data["Low"].iloc[i - 2]

        if bull_fvg:
            fvgs.append({
                "type": "Bullish FVG",
                "start": data["Datetime"].iloc[i - 2],
                "end": ts,
                "bottom": data["High"].iloc[i - 2],
                "top": data["Low"].iloc[i]
            })
            # Order Block: Bullish மூவிற்கு முன் இருந்த கடைசி Red Candle
            if data["Close"].iloc[i - 2] < data["Open"].iloc[i - 2]:
                order_blocks.append({
                    "type": "Bullish OB",
                    "time": data["Datetime"].iloc[i - 2],
                    "low": data["Low"].iloc[i - 2],
                    "high": data["High"].iloc[i - 2]
                })

        if bear_fvg:
            fvgs.append({
                "type": "Bearish FVG",
                "start": data["Datetime"].iloc[i - 2],
                "end": ts,
                "top": data["Low"].iloc[i - 2],
                "bottom": data["High"].iloc[i]
            })
            # Order Block: Bearish மூவிற்கு முன் இருந்த கடைசி Green Candle
            if data["Close"].iloc[i - 2] > data["Open"].iloc[i - 2]:
                order_blocks.append({
                    "type": "Bearish OB",
                    "time": data["Datetime"].iloc[i - 2],
                    "low": data["Low"].iloc[i - 2],
                    "high": data["High"].iloc[i - 2]
                })

        # --- ஏற்கனவே டிரேட் ஓடிக்கொண்டிருந்தால் SL / Target செக் ---
        if in_trade and active_trade is not None:
            entry = active_trade["Entry Price"]
            sl = active_trade["SL"]
            tp = active_trade["Target"]
            direction = active_trade["Type"]

            if direction == "BUY":
                fav_move = row["High"] - entry
                adv_move = entry - row["Low"]
                active_trade["MFE"] = max(active_trade["MFE"], fav_move)
                active_trade["MAE"] = max(active_trade["MAE"], adv_move)

                if row["Low"] <= sl:
                    pnl = (sl - entry) - brokerage_pts
                    active_trade["Exit Time"] = ts
                    active_trade["Exit Price"] = round(sl, 2)
                    active_trade["PnL (Pts)"] = round(pnl, 2)
                    active_trade["Result"] = "LOSS ❌"
                    active_trade["In-Trade Story"] = (
                        f"அதிகபட்சம் +{round(active_trade['MFE'], 1)} pts லாபம் சென்றது; "
                        f"பின் Selling அழுத்தத்தால் {round(active_trade['MAE'], 1)} pts கீழே இறங்கியது."
                    )
                    active_trade["Exit Reason"] = "Order Block / Swing Low உடைக்கப்பட்டு Stop-Loss ஹிட் ஆனது."
                    trades.append(active_trade)
                    in_trade = False
                    active_trade = None
                elif row["High"] >= tp:
                    pnl = (tp - entry) - brokerage_pts
                    active_trade["Exit Time"] = ts
                    active_trade["Exit Price"] = round(tp, 2)
                    active_trade["PnL (Pts)"] = round(pnl, 2)
                    active_trade["Result"] = "PROFIT ✅"
                    active_trade["In-Trade Story"] = (
                        f"அதிகபட்சம் -{round(active_trade['MAE'], 1)} pts வரை மட்டுமே Drawdown சென்றது; "
                        f"பின் வலுவான Buying மூவ் வந்தது."
                    )
                    active_trade["Exit Reason"] = f"1:{rr_ratio} Target துல்லியமாக ஹிட் ஆனது."
                    trades.append(active_trade)
                    in_trade = False
                    active_trade = None

            elif direction == "SELL":
                fav_move = entry - row["Low"]
                adv_move = row["High"] - entry
                active_trade["MFE"] = max(active_trade["MFE"], fav_move)
                active_trade["MAE"] = max(active_trade["MAE"], adv_move)

                if row["High"] >= sl:
                    pnl = (entry - sl) - brokerage_pts
                    active_trade["Exit Time"] = ts
                    active_trade["Exit Price"] = round(sl, 2)
                    active_trade["PnL (Pts)"] = round(pnl, 2)
                    active_trade["Result"] = "LOSS ❌"
                    active_trade["In-Trade Story"] = (
                        f"அதிகபட்சம் +{round(active_trade['MFE'], 1)} pts லாபம் சென்றது; "
                        f"பின் Buying அழுத்தத்தால் {round(active_trade['MAE'], 1)} pts மேலே சென்றது."
                    )
                    active_trade["Exit Reason"] = "Order Block / Swing High உடைக்கப்பட்டு Stop-Loss ஹிட் ஆனது."
                    trades.append(active_trade)
                    in_trade = False
                    active_trade = None
                elif row["Low"] <= tp:
                    pnl = (entry - tp) - brokerage_pts
                    active_trade["Exit Time"] = ts
                    active_trade["Exit Price"] = round(tp, 2)
                    active_trade["PnL (Pts)"] = round(pnl, 2)
                    active_trade["Result"] = "PROFIT ✅"
                    active_trade["In-Trade Story"] = (
                        f"அதிகபட்சம் -{round(active_trade['MAE'], 1)} pts வரை மட்டுமே Drawdown சென்றது; "
                        f"பின் வலுவான Selling மூவ் வந்தது."
                    )
                    active_trade["Exit Reason"] = f"1:{rr_ratio} Target துல்லியமாக ஹிட் ஆனது."
                    trades.append(active_trade)
                    in_trade = False
                    active_trade = None
            continue

        # --- புதிய என்ட்ரி தேடுதல் (Unlimited Backtest Mode) ---
        if use_killzone and not is_in_killzone(ts, market_type):
            continue

        # BUY Setup: SSL Liquidity Sweep அல்லது Bullish FVG + Bullish Close
        ssl_sweep = (
            last_swing_low is not None
            and row["Low"] < last_swing_low
            and row["Close"] > last_swing_low
            and row["Close"] > row["Open"]
        )
        if ssl_sweep or (bull_fvg and row["Close"] > row["Open"]):
            entry_price = row["Close"]
            sl_price = min(row["Low"], data["Low"].iloc[i - 1])
            risk = entry_price - sl_price
            if risk > 0:
                tp_price = entry_price + (risk * rr_ratio)
                reason = (
                    f"SSL Liquidity ({round(last_swing_low, 1)}) Sweep + Bullish Rejection"
                    if ssl_sweep
                    else "Bullish Displacement + Fair Value Gap (FVG) Confirmation"
                )
                active_trade = {
                    "Entry Time": ts,
                    "Exit Time": None,
                    "Type": "BUY",
                    "Entry Price": round(entry_price, 2),
                    "SL": round(sl_price, 2),
                    "Target": round(tp_price, 2),
                    "Exit Price": None,
                    "PnL (Pts)": 0.0,
                    "Result": "OPEN",
                    "MFE": 0.0,
                    "MAE": 0.0,
                    "Entry Reason": reason,
                    "In-Trade Story": "",
                    "Exit Reason": ""
                }
                in_trade = True
                continue

        # SELL Setup: BSL Liquidity Sweep அல்லது Bearish FVG + Bearish Close
        bsl_sweep = (
            last_swing_high is not None
            and row["High"] > last_swing_high
            and row["Close"] < last_swing_high
            and row["Close"] < row["Open"]
        )
        if bsl_sweep or (bear_fvg and row["Close"] < row["Open"]):
            entry_price = row["Close"]
            sl_price = max(row["High"], data["High"].iloc[i - 1])
            risk = sl_price - entry_price
            if risk > 0:
                tp_price = entry_price - (risk * rr_ratio)
                reason = (
                    f"BSL Liquidity ({round(last_swing_high, 1)}) Sweep + Bearish Rejection"
                    if bsl_sweep
                    else "Bearish Displacement + Fair Value Gap (FVG) Confirmation"
                )
                active_trade = {
                    "Entry Time": ts,
                    "Exit Time": None,
                    "Type": "SELL",
                    "Entry Price": round(entry_price, 2),
                    "SL": round(sl_price, 2),
                    "Target": round(tp_price, 2),
                    "Exit Price": None,
                    "PnL (Pts)": 0.0,
                    "Result": "OPEN",
                    "MFE": 0.0,
                    "MAE": 0.0,
                    "Entry Reason": reason,
                    "In-Trade Story": "",
                    "Exit Reason": ""
                }
                in_trade = True

    trades_df = pd.DataFrame(trades)
    return trades_df, fvgs[-25:], order_blocks[-15:], liquidity_levels[-15:]
  
