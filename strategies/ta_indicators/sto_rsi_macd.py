import pandas as pd
import numpy as np


class STORSIMACDStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def sto_rsi_macd(self,
                     k_period: int,
                     smoothing_k: int,
                     d_period: int,
                     ema_fast: int,
                     ema_slow: int,
                     ema_sign: int,
                     rsi_window: int,
                     lags: int,
                     shift_position: int):

        # MACD
        self.data["EMA_FAST"] = self.data.Close.ewm(span=ema_fast, adjust=False).mean()
        self.data["EMA_SLOW"] = self.data.Close.ewm(span=ema_slow, adjust=False).mean()
        self.data["MACD"] = self.data.EMA_FAST - self.data.EMA_SLOW
        self.data["MACD_SIGNAL"] = self.data.MACD.ewm(span=ema_sign, adjust=False).mean()
        self.data["MACD_DIFF"] = self.data.MACD - self.data.MACD_SIGNAL

        # Stochastic
        self.data["n_high"] = self.data['High'].rolling(k_period).max()
        self.data["n_low"] = self.data['Low'].rolling(k_period).min()
        self.data["%K"] = (self.data["Close"] - self.data["n_low"]) * 100 / (self.data["n_high"] - self.data["n_low"])
        self.data["%K"] = self.data["%K"].ewm(span=smoothing_k, adjust=False).mean()
        self.data["%D"] = self.data["%K"].rolling(d_period).mean()

        # RSI
        self.data["price_change"] = self.data.Close.pct_change()
        self.data["upMove"] = self.data.price_change.apply(lambda x: x if x > 0 else 0)
        self.data["downMove"] = self.data.price_change.apply(lambda x: abs(x) if x < 0 else 0)
        self.data["avg_Up"] = self.data.upMove.ewm(span=rsi_window, adjust=False).mean()
        self.data["avg_Down"] = self.data.downMove.ewm(span=rsi_window, adjust=False).mean()

        self.data["RS"] = self.data.avg_Up / self.data.avg_Down
        self.data["RSI"] = self.data.RS.apply(lambda x: 100 - (100 / (x + 1)))

        self.data.dropna(inplace=True)

        self.decide(lags=lags, shift_position=shift_position)

        self.data.dropna(inplace=True)

        return self.data

    def get_trigger(self, lags: int, buy=True):
        dfx = pd.DataFrame()
        for i in range(1, lags + 1):
            if buy:
                mask = (self.data["%K"].shift(i) < 20) & (self.data["%D"].shift(i) < 20)
            else:
                mask = (self.data["%K"].shift(i) > 80) & (self.data["%D"].shift(i) > 80)
            dfx = dfx.append(mask, ignore_index=True)
        return dfx.sum(axis=0)

    def decide(self, lags: int, shift_position: int):
        self.data["buy_trigger"] = np.where(self.get_trigger(lags=lags, buy=True), 1, 0)
        self.data["sell_trigger"] = np.where(self.get_trigger(lags=lags, buy=False), 1, 0)

        self.data["position"] = 0

        buy_cond = (self.data["buy_trigger"]) & \
                   (self.data["%K"].between(20, 80)) & \
                   (self.data["%D"].between(20, 80)) & \
                   (self.data["RSI"] > 50) & \
                   (self.data["MACD_DIFF"] > 0)

        sell_cond = (self.data["sell_trigger"]) & \
                    (self.data["%K"].between(20, 80)) & \
                    (self.data["%D"].between(20, 80)) & \
                    (self.data["RSI"] < 50) & \
                    (self.data["MACD_DIFF"] < 0)

        self.data.loc[buy_cond, "position"] = 1
        self.data.loc[sell_cond, "position"] = -1

        self.data["position"] = self.data["position"].shift(shift_position)
