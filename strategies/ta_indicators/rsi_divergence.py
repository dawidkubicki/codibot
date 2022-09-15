import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from collections import deque
from copy import deepcopy

pd.options.mode.chained_assignment = None


class RSIDivergenceStrategy:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def rsi(self,
            window: int,
            frame: int,
            K: int,
            ema_s: int,
            ema_m: int,
            rsi_small: int,
            rsi_big: int,
            lags: int,
            divergence_regular: bool) -> pd.DataFrame:
        self.data["price_change"] = self.data.Close.pct_change()
        self.data["EMA_S"] = self.data.Close.ewm(span=ema_s, adjust=False).mean()
        self.data["EMA_M"] = self.data.Close.ewm(span=ema_m, adjust=False).mean()
        self.data["upMove"] = self.data.price_change.apply(lambda x: x if x > 0 else 0)
        self.data["downMove"] = self.data.price_change.apply(lambda x: abs(x) if x < 0 else 0)
        self.data["avg_Up"] = self.data.upMove.ewm(span=window, adjust=False).mean()
        self.data["avg_Down"] = self.data.downMove.ewm(span=window, adjust=False).mean()

        self.data.dropna(inplace=True)

        self.data["RS"] = self.data.avg_Up / self.data.avg_Down
        self.data["RSI"] = self.data.RS.apply(lambda x: 100 - (100 / (x + 1)))

        self.data.dropna(inplace=True)

        self.divergence_strategy(frame=frame,
                                 K=K,
                                 rsi_small=rsi_small,
                                 rsi_big=rsi_big,
                                 lags=lags,
                                 divergence_regular=divergence_regular)

        return self.data

    def get_hh_index(self, data, frame: int, K: int):
        extrema = self.get_higher_highs(data, frame, K)
        idx = np.array([i[-1] + frame for i in extrema])
        return idx[np.where(idx < len(data))]

    def get_lh_index(self, data, frame: int, K: int):
        extrema = self.get_lower_highs(data, frame, K)
        idx = np.array([i[-1] + frame for i in extrema])
        return idx[np.where(idx < len(data))]

    def get_ll_index(self, data, frame: int, K: int):
        extrema = self.get_lower_lows(data, frame, K)
        idx = np.array([i[-1] + frame for i in extrema])
        return idx[np.where(idx < len(data))]

    def get_hl_index(self, data, frame: int, K: int):
        extrema = self.get_higher_lows(data, frame, K)
        idx = np.array([i[-1] + frame for i in extrema])
        return idx[np.where(idx < len(data))]

    def get_peaks(self, data_frame, key: str, frame: int, K: int):
        data = data_frame
        hh_idx = self.get_hh_index(data[key], frame, K)
        lh_idx = self.get_lh_index(data[key], frame, K)
        ll_idx = self.get_ll_index(data[key], frame, K)
        hl_idx = self.get_hl_index(data[key], frame, K)

        data[f'{key}_highs'] = 0
        data[f'{key}_highs'].iloc[hh_idx] = 1
        data[f'{key}_highs'].iloc[lh_idx] = -1
        data[f'{key}_highs'] = data[f'{key}_highs'].ffill().fillna(0)
        data[f'{key}_lows'] = 0
        data[f'{key}_lows'].iloc[ll_idx] = 1
        data[f'{key}_lows'].iloc[hl_idx] = -1
        data[f'{key}_lows'] = data[f'{key}_highs'].ffill().fillna(0)

        return data

    def get_rsi_trigger(self, lags: int, rsi_small: int, rsi_big: int, buy=True, divergence_regular=True):
        dfx = pd.DataFrame()
        for i in range(1, lags + 1):
            if divergence_regular:
                if buy:
                    mask = (self.data["RSI"].shift(i) > rsi_small) & (self.data["RSI"].shift(i) < rsi_big)
                else:
                    mask = (self.data["RSI"].shift(i) < rsi_small)
                dfx = dfx.append(mask, ignore_index=True)
            else:
                if buy:
                    mask = (self.data["RSI"].shift(i) < rsi_small)
                else:
                    mask = (self.data["RSI"].shift(i) > rsi_small) & (self.data["RSI"].shift(i) < rsi_big)
                dfx = dfx.append(mask, ignore_index=True)
        return dfx.sum(axis=0)

    def divergence_strategy(self, frame: int, K: int, rsi_small: int, rsi_big: int, lags: int, divergence_regular=True):

        self.data = self.get_peaks(deepcopy(self.data), key='Close', frame=frame, K=K)
        self.data = self.get_peaks(deepcopy(self.data), key='RSI', frame=frame, K=K)

        if divergence_regular:
            self.data["buy_trigger"] = np.where(self.get_rsi_trigger(lags=lags,
                                                                     buy=True,
                                                                     rsi_small=rsi_small,
                                                                     rsi_big=rsi_big,
                                                                     divergence_regular=divergence_regular), 1, 0)
            self.data["sell_trigger"] = np.where(self.get_rsi_trigger(lags=lags,
                                                                      buy=False,
                                                                      rsi_small=rsi_small,
                                                                      rsi_big=rsi_big,
                                                                      divergence_regular=divergence_regular), 1, 0)

            buy_cond = (self.data["buy_trigger"]) & \
                       (self.data['Close_lows'] == -1) & \
                       (self.data['RSI_lows'] == 1)

            sell_cond = (self.data["sell_trigger"]) & \
                        (self.data['Close_highs'] == 1) & \
                        (self.data['RSI_highs'] == -1)

            self.data["position"] = 0
            self.data.loc[buy_cond, "position"] = 1
            self.data.loc[sell_cond, "position"] = -1

        else:
            self.data["buy_trigger"] = np.where(self.get_rsi_trigger(lags=lags,
                                                                     buy=True,
                                                                     rsi_small=rsi_small,
                                                                     rsi_big=rsi_big,
                                                                     divergence_regular=divergence_regular), 1, 0)
            self.data["sell_trigger"] = np.where(self.get_rsi_trigger(lags=lags,
                                                                      buy=False,
                                                                      rsi_small=rsi_small,
                                                                      rsi_big=rsi_big,
                                                                      divergence_regular=divergence_regular
                                                                      ), 1, 0)

            buy_cond = (self.data["buy_trigger"]) & \
                       (self.data['Close_lows'] == 1) & \
                       (self.data['RSI_highs'] == -1)

            sell_cond = (self.data["sell_trigger"]) & \
                        (self.data['Close_highs'] == -1) & \
                        (self.data['RSI_highs'] == 1)

            self.data["position"] = 0
            self.data.loc[buy_cond, "position"] = 1
            self.data.loc[sell_cond, "position"] = -1

    def get_higher_lows(self, data, frame: int, K: int):
        """
        frame: how many candles from the past and future need to be analyse
        K: determines how many consecutive lows need to be higher
        """
        low_idx = argrelextrema(data.values, np.less, order=frame)[0]
        lows = data.iloc[low_idx]

        # Make sure that lows are higher than previous lows
        extrema = []
        ex_deque = deque(maxlen=K)
        for i, idx in enumerate(low_idx):
            if i == 0:
                ex_deque.append(idx)
                continue
            if lows[i] < lows[i - 1]:
                ex_deque.clear()
            ex_deque.append(idx)
            if len(ex_deque) == K:
                extrema.append(ex_deque.copy())

        return extrema

    def get_lower_highs(self, data, frame: int, K: int):
        """
        frame: how many candles from the past and future need to be analyse
        K: determines how many consecutive highs need to be higher
        """
        high_idx = argrelextrema(data.values, np.greater, order=frame)[0]
        highs = data.iloc[high_idx]

        # Make sure that highs are lower than previous highs
        extrema = []
        ex_deque = deque(maxlen=K)
        for i, idx in enumerate(high_idx):
            if i == 0:
                ex_deque.append(idx)
                continue
            if highs[i] > highs[i - 1]:
                ex_deque.clear()
            ex_deque.append(idx)
            if len(ex_deque) == K:
                extrema.append(ex_deque.copy())

        return extrema

    def get_higher_highs(self, data, frame: int, K: int):
        """
        frame: how many candles from the past and future need to be analyse
        K: determines how many consecutive highs need to be higher
        """
        high_idx = argrelextrema(data.values, np.greater, order=frame)[0]
        highs = data.iloc[high_idx]

        # Make sure that highs are higher than previous highs
        extrema = []
        ex_deque = deque(maxlen=K)
        for i, idx in enumerate(high_idx):
            if i == 0:
                ex_deque.append(idx)
                continue
            if highs[i] < highs[i - 1]:
                ex_deque.clear()
            ex_deque.append(idx)
            if len(ex_deque) == K:
                extrema.append(ex_deque.copy())

        return extrema

    def get_lower_lows(self, data, frame: int, K: int):
        """
        frame: how many candles from the past and future need to be analyse
        K: determines how many consecutive lows need to be lower
        """
        low_idx = argrelextrema(data.values, np.less, order=frame)[0]
        lows = data.iloc[low_idx]

        # Make sure that lows are lower than previous lows
        extrema = []
        ex_deque = deque(maxlen=K)
        for i, idx in enumerate(low_idx):
            if i == 0:
                ex_deque.append(idx)
                continue
            if lows[i] > lows[i - 1]:
                ex_deque.clear()
            ex_deque.append(idx)
            if len(ex_deque) == K:
                extrema.append(ex_deque.copy())

        return extrema
