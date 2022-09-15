import pandas as pd


class EMAStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    """
    Technical indicator - buy when short ma is above long ma, sell when long ma is above.
    Value indicator - buy when long ma is above long ma, sell when short ma is above.
    """
    def double_ema(self, ema_s: int, ema_l: int, technical=True, shifting=False) -> pd.DataFrame:
        self.data["EMA_S"] = self.data.Close.ewm(span=ema_s, adjust=False).mean()
        self.data["EMA_L"] = self.data.Close.ewm(span=ema_l, adjust=False).mean()

        self.data.dropna(inplace=True)

        if shifting:
            if technical:
                cond1 = (self.data.EMA_S > self.data.EMA_L) & (self.data.shift(1).EMA_S < self.data.shift(1).EMA_L)
                cond2 = (self.data.EMA_S < self.data.EMA_L) & (self.data.shift(1).EMA_S > self.data.shift(1).EMA_L)
            else:
                cond1 = (self.data.EMA_S < self.data.EMA_L) & (self.data.shift(1).EMA_S > self.data.shift(1).EMA_L)
                cond2 = (self.data.EMA_S > self.data.EMA_L) & (self.data.shift(1).EMA_S < self.data.shift(1).EMA_L)
        else:
            if technical:
                cond1 = (self.data.EMA_S > self.data.EMA_L)
                cond2 = (self.data.EMA_S < self.data.EMA_L)
            else:
                cond1 = (self.data.EMA_S < self.data.EMA_L)
                cond2 = (self.data.EMA_S > self.data.EMA_L)

        self.data["position"] = 0
        self.data.loc[cond1, "position"] = 1
        self.data.loc[cond2, "position"] = -1

        return self.data

    """
    Technical indicator - buy when short and medium is above long ma, sell in the opposite.
    Value indicator - buy when short and medium is below long ma, sell in the opposite.
    """
    def triple_ema(self, ema_s: int, ema_m: int, ema_l: int, technical=True, shifting=True) -> pd.DataFrame:
        self.data["EMA_S"] = self.data.Close.ewm(span=ema_s, adjust=False).mean()
        self.data["EMA_M"] = self.data.Close.ewm(span=ema_m, adjust=False).mean()
        self.data["EMA_L"] = self.data.Close.ewm(span=ema_l, adjust=False).mean()

        self.data.dropna(inplace=True)

        if shifting:
            if technical:
                cond1 = (self.data.EMA_S > self.data.EMA_M) & (self.data.EMA_M > self.data.EMA_L) & \
                        (self.data.shift(1).EMA_S < self.data.EMA_M) & (self.data.shift(1).EMA_M < self.data.shift(1).EMA_L)
                cond2 = (self.data.EMA_S < self.data.EMA_M) & (self.data.EMA_M < self.data.EMA_L) & \
                        (self.data.shift(1).EMA_S > self.data.EMA_M) & (self.data.shift(1).EMA_M > self.data.shift(1).EMA_L)
            else:
                cond1 = (self.data.EMA_S < self.data.EMA_M) & (self.data.EMA_M < self.data.EMA_L) & \
                        (self.data.shift(1).EMA_S > self.data.EMA_M) & (
                                    self.data.shift(1).EMA_M > self.data.shift(1).EMA_L)
                cond2 = (self.data.EMA_S > self.data.EMA_M) & (self.data.EMA_M > self.data.EMA_L) & \
                        (self.data.shift(1).EMA_S < self.data.EMA_M) & (
                                    self.data.shift(1).EMA_M < self.data.shift(1).EMA_L)

        else:
            if technical:
                cond1 = (self.data.EMA_S > self.data.EMA_M) & (self.data.EMA_M > self.data.EMA_L)
                cond2 = (self.data.EMA_S < self.data.EMA_M) & (self.data.EMA_M < self.data.EMA_L)
            else:
                cond1 = (self.data.EMA_S < self.data.EMA_M) & (self.data.EMA_M < self.data.EMA_L)
                cond2 = (self.data.EMA_S > self.data.EMA_M) & (self.data.EMA_M > self.data.EMA_L)

        self.data["position"] = 0
        self.data.loc[cond1, "position"] = 1
        self.data.loc[cond2, "position"] = -1

        return self.data


