from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, classification_report
import matplotlib.pyplot as plt
from hmmlearn import hmm
import xgboost as xgb


def train_HMM(df, features):
    hmm_data = df[features]
    hmm_model = hmm.GaussianHMM(n_components=4, covariance_type="diag", n_iter=100, random_state=42)
    hmm_model.fit(hmm_data)
    df['MarketRegime'] = hmm_model.predict(hmm_data)


def destree_regressor(df, features):
    pass


def destree_class(df, features):
    pass


def train_exgboost(X_train, y_train):
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=500,
        learning_rate=0.01,
        max_depth=7,
        subsample=0.7,
        colsample_bytree=0.7,
        random_state=42
    )

    model.fit(X_train, y_train, verbose=False)
    return model


def random_forest_regr(df):
    pass


def random_forst_class(df):
    pass
