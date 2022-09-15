import pandas as pd

from backtester.model.backtester import Backtester
from strategies.ta_indicators.rsi_divergence import RSIDivergenceStrategy
from exit_rules.backtesting_exit_rules import ExitRules
from tqdm import tqdm
import copy
from itertools import product


class RSI:
    def __init__(self,
                 key: str,
                 secret: str,
                 use_testnet: bool,
                 interval: str,
                 start: int,
                 symbols: list,
                 strategy: str,
                 tc: float,
                 period_cagr="month"):
        self.backtester = Backtester(key=key,
                                     secret=secret,
                                     use_testnet=use_testnet,
                                     symbols=symbols,
                                     interval=interval,
                                     start=start,
                                     tc=tc,
                                     period_cagr=period_cagr)
        self.rsi_data = {}
        self.triple_ema_data = {}
        self.backtested_data = {}
        self.EMA_range = ()
        self.strategy = strategy
        self.performance_data = pd.DataFrame

    def rsi(self,
            window: int,
            frame: int,
            K: int,
            ema_s: int,
            ema_m: int,
            rsi_small: int,
            rsi_big: int,
            lags: int,
            divergence_regular: bool,
            stop_loss=1.5,
            atr_window=14,
            atr_stop_loss=True,
            fixed_stop_loss=False,
            trailing_stop_loss=False,
            ema_calc=True,
            own_smoothing=False,
            ):
        new_data = copy.deepcopy(self.backtester.data)
        for pairs, data in new_data.items():
            strategy = RSIDivergenceStrategy(data)
            self.rsi_data[pairs] = strategy.rsi(window=window,
                                                frame=frame,
                                                K=K,
                                                ema_s=ema_s,
                                                ema_m=ema_m,
                                                rsi_big=rsi_big,
                                                rsi_small=rsi_small,
                                                lags=lags,
                                                divergence_regular=divergence_regular)

            if fixed_stop_loss and not trailing_stop_loss and not atr_stop_loss:
                self.rsi_data[pairs] = ExitRules(data).fixed_stop_loss(stop_loss)
            elif trailing_stop_loss and not fixed_stop_loss and not atr_stop_loss:
                self.rsi_data[pairs] = ExitRules(data).trailing_stop_loss(stop_loss)
            elif atr_stop_loss and not fixed_stop_loss and not trailing_stop_loss:
                self.rsi_data[pairs] = ExitRules(data).atr_stop_loss(window=atr_window,
                                                                     stop_loss=stop_loss,
                                                                     ema_calc=ema_calc,
                                                                     own_smoothing=own_smoothing)

    def run_backtest(self):
        if self.rsi_data is None:
            print("Implement strategy firstly.")
        else:
            self.backtested_data = self.backtester.test_strategy(self.rsi_data)
            return self.backtested_data

    def measure_performance(self, print_performance=False):
        if self.backtested_data is not None:
            self.backtester.results = copy.deepcopy(self.backtested_data)
            scores = self.backtester.measure_performance()
            if print_performance:
                self.backtester.print_performance()
            return scores
        else:
            print("There's no backtested data.")

    def calculate_performance(self) -> dict:
        if self.strategy == "rsi":
            scores = {}
            assets = self.performance_data["Asset"].unique()

            for asset in assets:
                indexes = self.performance_data[self.performance_data["Asset"] == asset]["cstrategy"].nlargest(
                    3).index.values
                window, frame, k, ema_s, ema_m, rsi_buy, rsi_sell, creturns, cstrategy = \
                    [], [], [], [], [], [], [], [], []
                for idx in indexes:
                    window.append(int(self.performance_data["window"].iloc[int(idx)]))
                    frame.append(int(self.performance_data["frame"].iloc[int(idx)]))
                    k.append(int(self.performance_data["K"].iloc[int(idx)]))
                    ema_s.append(int(self.performance_data["EMA_S"].iloc[int(idx)]))
                    ema_m.append(int(self.performance_data["EMA_M"].iloc[int(idx)]))
                    rsi_buy.append(int(self.performance_data["rsi_buy_thresh"].iloc[int(idx)]))
                    rsi_sell.append(int(self.performance_data["rsi_sell_thresh"].iloc[int(idx)]))
                    creturns.append(float(self.performance_data["creturns"].iloc[int(idx)]))
                    cstrategy.append(float(self.performance_data["cstrategy"].iloc[int(idx)]))
                scores[asset] = [{"window": window},
                                 {"frame": frame},
                                 {"K": k},
                                 {"EMA_S": ema_s},
                                 {"EMA_M": ema_m},
                                 {"rsi_buy": rsi_buy},
                                 {"rsi_sell": rsi_sell},
                                 {"creturns": creturns},
                                 {"cstrategy": cstrategy}]

            return self.backtester.dict_to_json(scores)

    def all_combinantion(self,
                         window_range=None,
                         frame_range=None,
                         k_range=None,
                         ema_s_range=None,
                         ema_m_range=None,
                         rsi_buy_range=None,
                         rsi_sell_range=None):

        comb_creturns = []
        comb_cstrategy = []
        comb_pair = []
        comb_window, comb_frame, comb_k, comb_ema_s, comb_ema_m, comb_rsi_buy, comb_rsi_sell = [], [], [], [], [], [], []

        if self.strategy == "rsi":

            combinations = list(product(window_range,
                                        frame_range,
                                        k_range,
                                        ema_s_range,
                                        ema_m_range,
                                        rsi_buy_range,
                                        rsi_sell_range))
            for window, frame, k, ema_s, ema_m, rsi_buy, rsi_sell in tqdm(combinations):
                try:
                    self.rsi(window, frame, k, ema_s, ema_m, rsi_buy, rsi_sell)
                    self.run_backtest()
                    for pair, result in self.backtested_data.items():
                        comb_pair.append(pair)
                        comb_window.append(window)
                        comb_frame.append(frame)
                        comb_k.append(k)
                        comb_ema_s.append(ema_s)
                        comb_ema_m.append(ema_m)
                        comb_rsi_buy.append(rsi_buy)
                        comb_rsi_sell.append(rsi_sell)
                        comb_creturns.append(result["creturns"][-1])
                        comb_cstrategy.append(result["cstrategy"][-1])

                        self.performance_data = pd.DataFrame(list(zip(comb_pair,
                                                                      comb_window,
                                                                      comb_frame,
                                                                      comb_k,
                                                                      comb_ema_s,
                                                                      comb_ema_m,
                                                                      comb_rsi_buy,
                                                                      comb_rsi_sell,
                                                                      comb_creturns,
                                                                      comb_cstrategy)),
                                                             columns=["Asset",
                                                                      "window",
                                                                      "frame",
                                                                      "K",
                                                                      "EMA_S",
                                                                      "EMA_M"
                                                                      "rsi_buy_thresh",
                                                                      "rsi_sell_thresh",
                                                                      "creturns",
                                                                      "cstrategy"])
                except Exception as e:
                    print(e)

            self.calculate_performance()
