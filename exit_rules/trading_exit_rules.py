import pandas as pd
import numpy as np


class ExitRules:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.last_long_price = 0.0

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

    def trailing_stop_loss(self,
                           stop_loss,
                           long_price=0.0,
                           short_price=0.0,
                           last_price=pd.DataFrame(),
                           sl_long=pd.DataFrame(),
                           sl_short=pd.DataFrame()
                           ):
        """Set stop loss accordingly to the current highest close price"""

        active_SL = False
        first_iteration = True if len(last_price) <= 2 else False

        if not first_iteration:
            # HERE READ FROM SPECIAL PLACE LAST CHOSEN
            self.data["ST_long_price"] = last_price.Price.iloc[-1] * stop_loss
            self.data["ST_short_price"] = last_price.Price.iloc[-1] * (1 - stop_loss + 1)

            sl_cond = (self.data.Close < self.data.ST_long_price)
            bu_cond = (self.data.Close > self.data.ST_short_price)

            self.data.loc[sl_cond, "ST_long_active"] = 1
            self.data.loc[bu_cond, "ST_short_active"] = 1

            if self.data["ST_long_active"].iloc[-1] == 1:
                active_SL = True
            elif self.data["ST_short_active"].iloc[-1] == 1:
                active_SL = True

        if first_iteration:

            self.data["ST_long_price"] = long_price * stop_loss
            self.data["ST_long_active"] = 0

            self.data["ST_short_price"] = short_price * (1 - stop_loss + 1)
            self.data["ST_short_active"] = 0

            print(f"\nFIRST ITER: LONG STOP LOSS: {self.data['ST_long_price'].iloc[-1]}")
            print(f"FIRST ITER: SHORT STOP LOSS: {self.data['ST_short_price'].iloc[-1]}")

        if not active_SL:

            # If it's not empty
            if len(last_price) != 0:
                # Current Close price
                current_price = self.data.Close.iloc[-1]

                if len(last_price) > 1:

                    if current_price > last_price.Price.max():
                        self.data["ST_long_price"] = current_price * stop_loss

                        if len(sl_short) > 1:
                            self.data["ST_short_price"] = sl_short.ST_short_price.iloc[-1]

                    else:
                        if len(sl_long) > 1:
                            self.data["ST_long_price"] = sl_long.ST_long_price.iloc[-1]
                        self.data["ST_short_price"] = current_price * (1 - stop_loss + 1)

                    print(f"\nLONG STOP LOSS: {self.data['ST_long_price'].iloc[-1]}\n")
                    print(f"\nSHORT STOP LOSS: {self.data['ST_short_price'].iloc[-1]}\n")

            sl_cond = (self.data.Close < self.data.ST_long_price)
            bu_cond = (self.data.Close > self.data.ST_short_price)

            self.data.loc[sl_cond, "ST_long_active"] = 1
            self.data.loc[bu_cond, "ST_short_active"] = 1

        return self.data

    def atr_stop_loss(self,
                      window=14,
                      stop_loss=1.5,
                      own_smoothing=False,
                      last_price=pd.DataFrame(),
                      sl_long=pd.DataFrame(),
                      sl_short=pd.DataFrame()
                      ):
        """ The chandelier exit implementation"""

        active_SL = False
        first_iteration = True if len(last_price) <= 2 else False

        high_low = self.data['High'] - self.data['Low']
        high_close = np.abs(self.data['High'] - self.data['Close'].shift())
        low_close = np.abs(self.data['Low'] - self.data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        self.data["TR"] = np.max(ranges, axis=1)

        if not own_smoothing:
            self.data["ATR"] = self.data.TR.ewm(span=window, min_periods=window).mean()
        else:
            self.data["ATR"] = self.data.TR.ewm(span=window, adjust=False).mean()
            self.data["ATR"] = (self.data['ATR'].shift(1) * (window - 1) + self.data['TR']) / window

        if not first_iteration:
            self.data["ST_long_price"] = last_price.Price.iloc[-1] - (stop_loss * self.data.ATR)
            self.data["ST_short_price"] = last_price.Price.iloc[-1] + (stop_loss * self.data.ATR)

            sl_cond = (self.data.Close < self.data.ST_long_price)
            bu_cond = (self.data.Close > self.data.ST_short_price)

            self.data.loc[sl_cond, "ST_long_active"] = 1
            self.data.loc[bu_cond, "ST_short_active"] = 1

            if self.data["ST_long_active"].iloc[-1] == 1:
                active_SL = True
            elif self.data["ST_short_active"].iloc[-1] == 1:
                active_SL = True

        if first_iteration:
            self.data["ST_long_price"] = self.data.Close - (stop_loss * self.data.ATR)
            self.data["ST_long_active"] = 0

            self.data["ST_short_price"] = self.data.Close + (stop_loss * self.data.ATR)
            self.data["ST_short_active"] = 0

        if not active_SL:
            # If it's not empty
            if len(last_price) != 0:
                # Current Close price
                current_price = self.data.Close.iloc[-1]

                if len(last_price) > 1:

                    if current_price > last_price.Price.max():
                        self.data["ST_long_price"] = self.data["ST_long_price"] = current_price - (stop_loss * self.data.ATR)

                        if len(sl_short) > 1:
                            self.data["ST_short_price"] = sl_short.ST_short_price.iloc[-1]

                    else:
                        if len(sl_long) > 1:
                            self.data["ST_long_price"] = sl_long.ST_long_price.iloc[-1]
                        self.data["ST_short_price"] = current_price + (stop_loss * self.data.ATR)

            sl_cond = (self.data.Close < self.data.ST_long_price)
            bu_cond = (self.data.Close > self.data.ST_short_price)

            self.data.loc[sl_cond, "ST_long_active"] = 1
            self.data.loc[bu_cond, "ST_short_active"] = 1

        return self.data

    def fixed_take_profit(self, take_profit, long_price=0.0, short_price=0.0):
        """Take profit with the fixed price"""

        sl_cond = (self.data.Close > long_price * take_profit)
        bu_cond = (self.data.Close < short_price * (1 - take_profit + 1))

        self.data["TP_long_price"] = long_price * take_profit
        self.data["TP_long_active"] = 0
        self.data.loc[sl_cond, "TP_long_active"] = 1

        self.data["TP_short_price"] = short_price * (1 - take_profit + 1)
        self.data["TP_short_active"] = 0
        self.data.loc[bu_cond, "TP_short_active"] = 1

        return self.data

