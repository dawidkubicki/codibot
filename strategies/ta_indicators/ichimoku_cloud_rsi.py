import pandas as pd

class IchimokuCloudRSIStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def ichimoku_cloud_rsi(self,
                           # Ichimoku cloud
                           conversion_window: int,
                           base_window: int,
                           span_window: int,
                           leading_shift: int,
                           lagging_shift: int,
                           # RSI
                           rsi_window: int,
                           # EMA
                           ema_window: int):

        # Conversion Line / Tenkan-Sen
        conv_period_high = self.data["High"].rolling(window=conversion_window).max()
        conv_period_low = self.data["Low"].rolling(window=conversion_window).min()
        self.data["tenkan_sen"] = (conv_period_high + conv_period_low) / 2

        # Base Line / Kijun-Sen
        base_period_high = self.data["High"].rolling(window=base_window).max()
        base_period_low = self.data["Low"].rolling(window=base_window).min()
        self.data["kijun_sen"] = (base_period_high + base_period_low) / 2

        # Leading Span A / Senkou A
        self.data["senkou_span_a"] = ((self.data["tenkan_sen"] + self.data["kijun_sen"]) / 2).shift(leading_shift)

        # Leading Span B / Senkou B
        b_span_high = self.data["High"].rolling(window=span_window).max()
        b_span_low = self.data["Low"].rolling(window=span_window).min()
        self.data["senkou_span_b"] = ((b_span_high + b_span_low) / 2).shift(leading_shift)

        # Lagging Span / Chikou Span
        self.data["chikou_span"] = self.data["Close"].shift(-lagging_shift)

        # EMA
        self.data["EMA"] = self.data.Close.ewm(span=ema_window, adjust=False).mean()

        # RSI
        self.data["price_change"] = self.data.Close.pct_change()
        self.data["upMove"] = self.data.price_change.apply(lambda x: x if x > 0 else 0)
        self.data["downMove"] = self.data.price_change.apply(lambda x: abs(x) if x < 0 else 0)
        self.data["avg_Up"] = self.data.upMove.ewm(span=rsi_window, adjust=False).mean()
        self.data["avg_Down"] = self.data.downMove.ewm(span=rsi_window, adjust=False).mean()

        self.data["RS"] = self.data.avg_Up / self.data.avg_Down
        self.data["RSI"] = self.data.RS.apply(lambda x: 100 - (100 / (x + 1)))

        self.decide()

        self.data.dropna(inplace=True)

        return self.data

    def decide(self):
        self.data["position"] = 0

        buy_cond = (self.data["Close"] > self.data["senkou_span_a"]) & \
                   (self.data["Close"] > self.data["senkou_span_b"]) & \
                   ((self.data["senkou_span_a"] > self.data["senkou_span_b"]) > self.data["EMA"]) & \
                   (self.data["RSI"] > 70)

        sell_cond = (self.data["Close"] < self.data["senkou_span_a"]) & \
                    (self.data["Close"] < self.data["senkou_span_b"]) & \
                    ((self.data["senkou_span_a"] < self.data["senkou_span_b"]) < self.data["EMA"]) & \
                    (self.data["RSI"] < 30)

        self.data.loc[buy_cond, "position"] = 1
        self.data.loc[sell_cond, "position"] = -1
