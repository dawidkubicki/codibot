import pandas as pd


class MACDStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def macd(self, ema_s: int, ema_m: int, ema_signal: int, technical=True, shifting=False) -> pd.DataFrame:
        self.data["EMA_S"] = self.data.Close.ewm(span=ema_s, adjust=False).mean()
        self.data["EMA_M"] = self.data.Close.ewm(span=ema_m, adjust=False).mean()
        self.data["MACD"] = self.data.EMA_S - self.data.EMA_M
        self.data["SIGNAL"] = self.data.MACD.ewm(span=ema_signal, adjust=False).mean()

        self.data.dropna(inplace=True)

        if shifting:
            if technical:
                cond1 = (self.data.shift(1).MACD < self.data.shift(1).SIGNAL) & (self.data.MACD > self.data.SIGNAL)
                cond2 = (self.data.shift(1).MACD > self.data.shift(1).SIGNAL) & (self.data.MACD < self.data.SIGNAL)
            else:
                cond1 = (self.data.shift(1).MACD > self.data.shift(1).SIGNAL) & (self.data.MACD < self.data.SIGNAL)
                cond2 = (self.data.shift(1).MACD < self.data.shift(1).SIGNAL) & (self.data.MACD > self.data.SIGNAL)
        else:
            if technical:
                cond1 = (self.data.MACD > self.data.SIGNAL)
                cond2 = (self.data.MACD < self.data.SIGNAL)
            else:
                cond1 = (self.data.MACD < self.data.SIGNAL)
                cond2 = (self.data.MACD > self.data.SIGNAL)

        self.data["position"] = 0
        self.data.loc[cond1, "position"] = 1
        self.data.loc[cond2, "position"] = -1

        return self.data
