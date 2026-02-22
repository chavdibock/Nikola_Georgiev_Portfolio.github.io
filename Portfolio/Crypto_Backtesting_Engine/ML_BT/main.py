from numpy.distutils.system_info import dfftw_info

from utils import utils as utl
from models import models

if __name__ == "__main__":
    symbol = " BTCUSD"
    period = "1m"
    start_date = "2005-01-01"
    end_date = "2025-05-25"

    data = utl.get_data(symbol, period, start_date, end_date)

    # X_train, X_test, y_train, y_test = train_test_split(data, y, test_size=0.2, random_state=42)
    colls = ["Date", "Open", 'prev_day_open', 'prev_day_high', 'prev_day_low', 'prev_day_close', "gap_prc", "prev_high_low", 'return_1d', 'SMA_10',
             'SMA_20', 'SMA_50', 'SMA_100', 'MACD', 'MACD_signal', 'MACD_hist', 'RSI_21', "MarketRegime"]
    train_cosl = ['MACD', 'MACD_signal', 'MACD_hist', 'RSI_21', 'SMA_10', 'SMA_20', 'SMA_50', 'SMA_100', "MarketRegime"]
    predict = "actual_return"
    hmm_cols = ['MACD', 'MACD_signal', 'MACD_hist', 'RSI_21']

    models.train_HMM(df=data, features=hmm_cols)
    print(data)
    X_train, X_test, y_train, y_test = utl.split_to_sets(data, colls, predict)

    # utl.save_to_excel(df=X_train, symbol=symbol)
    Xgbst = models.train_exgboost(X_train[train_cosl], y_train)
    y_predict = Xgbst.predict(X_test[train_cosl])

    utl.plot_results(
        dates=X_test["Date"],
        actuals=y_test,
        predictions=y_predict
    )

    utl.show_importance(Xgbst, X_test[train_cosl])
    # print(X_train)
