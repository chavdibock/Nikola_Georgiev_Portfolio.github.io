import yfinance as yf
from datetime import datetime, timedelta
from scipy.interpolate import interp1d
import numpy as np


def filter_dates(dates):
    today = datetime.today().date()
    cutoff_date = today + timedelta(days=45)
    sorted_dates = sorted(datetime.strptime(date, "%Y-%m-%d").date() for date in dates)

    arr = []
    for i, date in enumerate(sorted_dates):
        if date >= cutoff_date:
            arr = [d.strftime("%Y-%m-%d") for d in sorted_dates[:i + 1]]
            break

    if len(arr) > 0:
        if arr[0] == today.strftime("%Y-%m-%d"):
            return arr[1:]
        return arr

    raise ValueError("No date 45 days or more in the future found.")


def yang_zhang(price_data, window=30, trading_periods=252):
    log_ho = (price_data['High'] / price_data['Open']).apply(np.log)
    log_lo = (price_data['Low'] / price_data['Open']).apply(np.log)
    log_co = (price_data['Close'] / price_data['Open']).apply(np.log)

    log_oc = (price_data['Open'] / price_data['Close'].shift(1)).apply(np.log)
    log_oc_sq = log_oc ** 2

    log_cc = (price_data['Close'] / price_data['Close'].shift(1)).apply(np.log)
    log_cc_sq = log_cc ** 2

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    close_vol = log_cc_sq.rolling(window=window).sum() / (window - 1)
    open_vol = log_oc_sq.rolling(window=window).sum() / (window - 1)
    window_rs = rs.rolling(window=window).sum() / (window - 1)

    k = 0.34 / (1.34 + ((window + 1) / (window - 1)))
    result = (open_vol + k * close_vol + (1 - k) * window_rs).apply(np.sqrt) * np.sqrt(trading_periods)

    return result.dropna().iloc[-1]


def build_term_structure(days, ivs):
    days = np.array(days)
    ivs = np.array(ivs)

    sort_idx = days.argsort()
    days = days[sort_idx]
    ivs = ivs[sort_idx]

    spline = interp1d(days, ivs, kind='linear', fill_value="extrapolate")

    def term_spline(dte):
        if dte < days[0]:
            return ivs[0]
        elif dte > days[-1]:
            return ivs[-1]
        else:
            return float(spline(dte))

    return term_spline


def get_current_price(ticker_obj):
    todays_data = ticker_obj.history(period='1d')
    return todays_data['Close'][0]


def get_prediction(ticker: str):
    try:
        ticker = ticker.strip().upper()
        stock = yf.Ticker(ticker)

        if len(stock.options) == 0:
            return f"No options data available for {ticker}"

        exp_dates = filter_dates(stock.options)

        options_chains = {exp: stock.option_chain(exp) for exp in exp_dates}
        underlying_price = get_current_price(stock)

        atm_iv = {}
        straddle = None

        for i, (exp_date, chain) in enumerate(options_chains.items()):
            calls, puts = chain.calls, chain.puts
            if calls.empty or puts.empty:
                continue

            call_idx = (calls['strike'] - underlying_price).abs().idxmin()
            put_idx = (puts['strike'] - underlying_price).abs().idxmin()

            call_iv = calls.loc[call_idx, 'impliedVolatility']
            put_iv = puts.loc[put_idx, 'impliedVolatility']
            atm_iv[exp_date] = (call_iv + put_iv) / 2.0

            if i == 0:
                call_mid = (calls.loc[call_idx, 'bid'] + calls.loc[call_idx, 'ask']) / 2
                put_mid = (puts.loc[put_idx, 'bid'] + puts.loc[put_idx, 'ask']) / 2
                straddle = call_mid + put_mid

        if not atm_iv:
            return "No ATM IV data available."

        today = datetime.today().date()
        dtes = [(datetime.strptime(exp, "%Y-%m-%d").date() - today).days for exp in atm_iv]
        ivs = list(atm_iv.values())

        term_spline = build_term_structure(dtes, ivs)
        slope = (term_spline(45) - term_spline(dtes[0])) / (45 - dtes[0])
        price_history = stock.history(period='3mo')
        iv30_rv30 = term_spline(30) / yang_zhang(price_history)
        avg_volume = price_history['Volume'].rolling(30).mean().dropna().iloc[-1]

        expected_move = f"{round(straddle / underlying_price * 100, 2)}%" if straddle else None

        return {
            'ticker': ticker,
            'avg_volume': avg_volume >= 1500000,
            'iv30_rv30': iv30_rv30 >= 1.25,
            'ts_slope_0_45': slope <= -0.00406,
            'expected_move': expected_move,
            'final_recommendation': (
                "Recommended" if (avg_volume >= 1500000 and iv30_rv30 >= 1.25 and slope <= -0.00406)
                else "Consider" if slope <= -0.00406 and (avg_volume >= 1500000 or iv30_rv30 >= 1.25)
                else "Avoid"
            )
        }
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == '__main__':

    stocks = ['COST', 'RY', 'DELL', 'NGG', 'CM', 'MRVL', 'ZS', 'FER', 'LI', 'NTAP', 'ULTA', 'HRL', 'COO', 'MDB', 'BBY', 'BURL', 'FUTU', 'GAP', 'ESTC', 'HLNE', 'ROIV', 'PATH', 'BBWI', 'TLX', 'DOOO', 'AMBA', 'FL', 'AEO', 'UVV', 'PD', 'CBRL', 'KSS', 'AMWD', 'SPTN', 'GES', 'BBW', 'CAL', 'TTGT', 'NGL', 'MOV', 'ESEA', 'DSX', 'AVD', 'KNDI', 'LVO', 'YI', 'CCG', 'JG', 'OPTX', 'DXLG', 'YAAS', 'RRGB', 'ALAR', 'YTRA', 'MAXN', 'PODC', 'MLEC', 'ARBK', 'REE', 'BOSC', 'CTRM', 'ENFY', 'BPT', 'TRIB', 'CMBM', 'NAAS', 'MRIN', 'NCNA', 'SPMC']


    for i in stocks:
        result = get_prediction(i)
        print(result)
