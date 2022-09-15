import pandas as pd
import numpy as np


class ExitRules:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def entry_long(self):
        """Add to data last entry trade price"""
        entry_buy_cond = (self.data.position == 1) & (
                (self.data.shift(1).position == 0) | (self.data.shift(1).position == -1))
        self.data["entry_long"] = np.nan
        self.data.loc[entry_buy_cond, "entry_long"] = self.data.Close
        self.data["entry_long"].fillna(method='ffill', inplace=True)
        self.data["entry_long"].replace(np.nan, 0, inplace=True)

    def fixed_stop_loss(self, stop_loss, long_price=0.0, short_price=0.0):
        """Fixed stop price provided as argument"""
        # Condition to change the stop-loss
        sl_cond = (self.data.Close < long_price * stop_loss)
        bu_cond = (self.data.Close > short_price * (1 - stop_loss + 1))

        self.data["ST_long_price"] = long_price * stop_loss
        self.data["ST_long_active"] = 0

        self.data["ST_short_price"] = short_price * (1 - stop_loss + 1)
        self.data["ST_short_active"] = 0

        self.data.loc[sl_cond, "ST_long_active"] = 1
        self.data.loc[bu_cond, "ST_short_active"] = 1

        return self.data

    def trailing_stop_loss(self, stop_loss):
        """Set stop loss accordingly to the current highest close price"""

        self.data["Benchmark"] = self.data.Close.cummax()

        self.data["ST_long_price"] = self.data.Benchmark * stop_loss
        self.data["ST_long_active"] = 0

        self.data["ST_short_price"] = (self.data.Benchmark * (1-stop_loss+1))
        self.data["ST_short_active"] = 0

        sl_cond = (self.data.Close < self.data.ST_long_price)
        bu_cond = (self.data.Close > self.data.ST_short_price)

        self.data.loc[sl_cond, "ST_long_active"] = 1
        self.data.loc[bu_cond, "ST_short_active"] = 1

        return self.data

    def atr_stop_loss(self, window=14, stop_loss=1.5, ema_calc=True, own_smoothing=False):
        """ The chandelier exit implementation"""

        high_low = self.data['High'] - self.data['Low']
        high_close = np.abs(self.data['High'] - self.data['Close'].shift())
        low_close = np.abs(self.data['Low'] - self.data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        self.data["TR"] = np.max(ranges, axis=1)

        if ema_calc:
            if not own_smoothing:
                self.data["ATR"] = self.data.TR.ewm(span=window, min_periods=window).mean()
            else:
                self.data["ATR"] = self.data.TR.ewm(span=window, adjust=False).mean()
                self.data["ATR"] = (self.data['ATR'].shift(1)*(window-1) + self.data['TR']) / window
        else:
            self.data["ATR"] = self.data.TR.rolling(window=window).mean().sum() / window

        self.data["ST_ATR"] = self.data.Close - (stop_loss*self.data.ATR)

        sl_cond = (self.data.Close <= self.data.ST_ATR) & (self.data.position == 1)
        # self.data.loc[sl_cond, "position"] = 0

        self.data["ST_active"] = 0
        self.data.loc[sl_cond, "ST_active"] = 1

        return self.data

    def fixed_take_profit(self, take_profit):
        """Take profit with the fixed price"""
        # Get the entry prices
        self.entry_buy()

        # Condition to change the stop-loss
        sl_cond = (self.data.Close >= self.data.entry_buy * take_profit) & (self.data.position == 1)
        # self.data.loc[sl_cond, "position"] = 0

        self.data["TP_active"] = 0
        self.data.loc[sl_cond, "TP_active"] = 1

        return self.data

    def trailing_take_profit(self, take_profit):
        pass
