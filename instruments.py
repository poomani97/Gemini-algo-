# இந்திய மார்க்கெட் Indices, F&O Stocks, Lot Size மற்றும் Strike Step விவரங்கள்

INSTRUMENT_CATEGORIES = {
    "1. Indian Indices (Index F&O)": {
        "NIFTY 50": {"symbol": "^NSEI", "lot_size": 75, "strike_step": 50, "market": "Indian"},
        "BANK NIFTY": {"symbol": "^NSEBANK", "lot_size": 30, "strike_step": 100, "market": "Indian"},
        "SENSEX (BSE)": {"symbol": "^BSESN", "lot_size": 20, "strike_step": 100, "market": "Indian"},
        "FINNIFTY": {"symbol": "NIFTY_FIN_SERVICE.NS", "lot_size": 65, "strike_step": 50, "market": "Indian"},
        "MIDCPNIFTY": {"symbol": "^NSEMDCP50", "lot_size": 120, "strike_step": 25, "market": "Indian"},
    },
    "2. Top NSE F&O Stocks": {
        "RELIANCE": {"symbol": "RELIANCE.NS", "lot_size": 500, "strike_step": 20, "market": "Indian"},
        "HDFC BANK": {"symbol": "HDFCBANK.NS", "lot_size": 550, "strike_step": 20, "market": "Indian"},
        "ICICI BANK": {"symbol": "ICICIBANK.NS", "lot_size": 700, "strike_step": 20, "market": "Indian"},
        "SBIN (SBI)": {"symbol": "SBIN.NS", "lot_size": 750, "strike_step": 10, "market": "Indian"},
        "TCS": {"symbol": "TCS.NS", "lot_size": 175, "strike_step": 50, "market": "Indian"},
        "INFOSYS": {"symbol": "INFY.NS", "lot_size": 400, "strike_step": 20, "market": "Indian"},
        "TATA MOTORS": {"symbol": "TATAMOTORS.NS", "lot_size": 550, "strike_step": 10, "market": "Indian"},
        "BAJAJ FINANCE": {"symbol": "BAJFINANCE.NS", "lot_size": 125, "strike_step": 100, "market": "Indian"},
        "AXIS BANK": {"symbol": "AXISBANK.NS", "lot_size": 625, "strike_step": 20, "market": "Indian"},
        "L&T (LT)": {"symbol": "LT.NS", "lot_size": 150, "strike_step": 50, "market": "Indian"},
        "ITC": {"symbol": "ITC.NS", "lot_size": 1600, "strike_step": 5, "market": "Indian"},
        "BHARTI AIRTEL": {"symbol": "BHARTIARTL.NS", "lot_size": 475, "strike_step": 20, "market": "Indian"},
    },
    "3. Global / Commodities / Crypto": {
        "GOLD (XAUUSD Futures)": {"symbol": "GC=F", "lot_size": 1, "strike_step": 10, "market": "Global"},
        "CRUDE OIL": {"symbol": "CL=F", "lot_size": 100, "strike_step": 1, "market": "Global"},
        "BITCOIN (BTCUSDT)": {"symbol": "BTC-USD", "lot_size": 1, "strike_step": 500, "market": "Global"},
    }
}


def generate_option_chain_strikes(spot_price, strike_step):
    """தற்போதைய Spot விலையை வைத்து ATM, ITM, OTM Strike Price பட்டியலை உருவாக்கும்."""
    atm = round(spot_price / strike_step) * strike_step
    strikes = []
    for offset in range(-5, 6):
        strike = int(atm + (offset * strike_step))
        if offset == 0:
            ce_tag, pe_tag = "ATM ⭐", "ATM ⭐"
        elif offset < 0:
            ce_tag, pe_tag = f"ITM ({abs(offset)})", f"OTM ({abs(offset)})"
        else:
            ce_tag, pe_tag = f"OTM ({offset})", f"ITM ({offset})"

        strikes.append({
            "CE Status": ce_tag,
            "Strike Price": strike,
            "PE Status": pe_tag
        })
    return int(atm), strikes
