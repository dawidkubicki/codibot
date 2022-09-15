import pandas as pd


class SMAStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    """
    Technical indicator - buy when short ma is above long ma, sell when long ma is above.
    Value indicator - buy when long ma is above long ma, sell when short ma is above.
    """

    def double_sma(self, sma_s: int, sma_l: int, technical=True, shifting=False) -> pd.DataFrame:
        self.data["SMA_S"] = self.data.Close.rolling(window=int(sma_s)).mean()
        self.data["SMA_L"] = self.data.Close.rolling(window=int(sma_l)).mean()

        self.data.dropna(inplace=True)

        if shifting:
            if technical:
                cond1 = (self.data.SMA_S > self.data.SMA_L) & (self.data.shift(1).SMA_S < self.data.shift(1).SMA_L)
                cond2 = (self.data.SMA_S < self.data.SMA_L) & (self.data.shift(1).SMA_S > self.data.shift(1).SMA_L)
            else:
                cond1 = (self.data.SMA_S < self.data.SMA_L) & (self.data.shift(1).SMA_S > self.data.shift(1).SMA_L)
                cond2 = (self.data.SMA_S > self.data.SMA_L) & (self.data.shift(1).SMA_S < self.data.shift(1).SMA_L)
        else:
            if technical:
                cond1 = (self.data.SMA_S > self.data.SMA_L)
                cond2 = (self.data.SMA_S < self.data.SMA_L)
            else:
                cond1 = (self.data.SMA_S < self.data.SMA_L)
                cond2 = (self.data.SMA_S > self.data.SMA_L)

        self.data["position"] = 0
        self.data.loc[cond1, "position"] = 1
        self.data.loc[cond2, "position"] = -1

        return self.data

    """
    Technical indicator - buy when short and medium is above long ma, sell in the opposite.
    Value indicator - buy when short and medium is below long ma, sell in the opposite.
    """

    def triple_sma(self, sma_s: int, sma_m: int, sma_l: int, technical=True, shifting=False) -> pd.DataFrame:
        self.data["SMA_S"] = self.data.Close.rolling(window=sma_s).mean()
        self.data["SMA_M"] = self.data.Close.rolling(window=sma_m).mean()
        self.data["SMA_L"] = self.data.Close.rolling(window=sma_l).mean()

        self.data.dropna(inplace=True)

        if shifting:
            if technical:
                cond1 = (self.data.SMA_S > self.data.SMA_M) & (self.data.SMA_M > self.data.SMA_L) & \
                        (self.data.shift(1).SMA_S < self.data.SMA_M) & (self.data.shift(1).SMA_M < self.data.SMA_L)
                cond2 = (self.data.SMA_S < self.data.SMA_M) & (self.data.SMA_M < self.data.SMA_L) & \
                        (self.data.shift(1).SMA_S > self.data.SMA_M) & (self.data.shift(1).SMA_M > self.data.SMA_L)
            else:
                cond1 = (self.data.SMA_S < self.data.SMA_M) & (self.data.SMA_M < self.data.SMA_L) & \
                        (self.data.shift(1).SMA_S > self.data.SMA_M) & (self.data.shift(1).SMA_M > self.data.SMA_L)
                cond2 = (self.data.SMA_S > self.data.SMA_M) & (self.data.SMA_M > self.data.SMA_L) & \
                        (self.data.shift(1).SMA_S < self.data.SMA_M) & (self.data.shift(1).SMA_M < self.data.SMA_L)
        else:
            if technical:
                cond1 = (self.data.SMA_S > self.data.SMA_M) & (self.data.SMA_M > self.data.SMA_L)
                cond2 = (self.data.SMA_S < self.data.SMA_M) & (self.data.SMA_M < self.data.SMA_L)
            else:
                cond1 = (self.data.SMA_S < self.data.SMA_M) & (self.data.SMA_M < self.data.SMA_L)
                cond2 = (self.data.SMA_S > self.data.SMA_M) & (self.data.SMA_M > self.data.SMA_L)

        self.data["position"] = 0
        self.data.loc[cond1, "position"] = 1
        self.data.loc[cond2, "position"] = -1

        return self.data
