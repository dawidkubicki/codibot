import pandas as pd

from backtester.model.backtester import Backtester
from strategies.ta_indicators.macd import MACDStrategy
from exit_rules.backtesting_exit_rules import ExitRules
from tqdm import tqdm
import copy
from itertools import product


class MACD:
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
        self.macd_data = {}
        self.triple_ema_data = {}
        self.backtested_data = {}
        self.EMA_range = ()
        self.strategy = strategy
        self.performance_data = pd.DataFrame

    def macd(self,
             ema_s: int,
             ema_m: int,
             ema_signal: int,
             stop_loss=1.5,
             atr_window=14,
             atr_stop_loss=True,
             fixed_stop_loss=False,
             trailing_stop_loss=False,
             ema_calc=True,
             own_smoothing=False,
             technical=True,
             shifting=False):
        new_data = copy.deepcopy(self.backtester.data)

        for pairs, data in new_data.items():

            strategy = MACDStrategy(data)
            self.macd_data[pairs] = strategy.macd(ema_s, ema_m, ema_signal, technical, shifting)

            if fixed_stop_loss and not trailing_stop_loss and not atr_stop_loss:
                self.macd_data[pairs] = ExitRules(data).fixed_stop_loss(stop_loss)
            elif trailing_stop_loss and not fixed_stop_loss and not atr_stop_loss:
                self.macd_data[pairs] = ExitRules(data).trailing_stop_loss(stop_loss)
            elif atr_stop_loss and not fixed_stop_loss and not trailing_stop_loss:
                self.macd_data[pairs] = ExitRules(data).atr_stop_loss(window=atr_window,
                                                                      stop_loss=stop_loss,
                                                                      ema_calc=ema_calc,
                                                                      own_smoothing=own_smoothing)

    def run_backtest(self):
        if self.macd_data is None:
            print("Implement strategy firstly.")
        else:
            self.backtested_data = self.backtester.test_strategy(self.macd_data)
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
        if self.strategy == "macd":
            scores = {}
            assets = self.performance_data["Asset"].unique()

            for asset in assets:
                indexes = self.performance_data[self.performance_data["Asset"] == asset]["cstrategy"].nlargest(
                    3).index.values
                ema_s, ema_m, ema_signal, creturns, cstrategy = [], [], [], [], []
                for idx in indexes:
                    ema_s.append(int(self.performance_data["EMA_S"].iloc[int(idx)]))
                    ema_m.append(int(self.performance_data["EMA_M"].iloc[int(idx)]))
                    ema_signal.append(int(self.performance_data["SIGNAL"].iloc[int(idx)]))
                    creturns.append(float(self.performance_data["creturns"].iloc[int(idx)]))
                    cstrategy.append(float(self.performance_data["cstrategy"].iloc[int(idx)]))
                scores[asset] = [{"ema_s": ema_s},
                                 {"ema_m": ema_m},
                                 {"ema_signal": ema_signal},
                                 {"creturns": creturns},
                                 {"cstrategy": cstrategy}]

            return self.backtester.dict_to_json(scores)

    def all_combinantion(self, EMA_S_range=None, EMA_M_range=None, EMA_signal_range=None, technical=True,
                         shifting=False):

        comb_creturns = []
        comb_cstrategy = []
        comb_pair = []
        comb_s, comb_m, comb_signal = [], [], []

        if self.strategy == "macd":

            combinations = list(product(EMA_S_range, EMA_M_range, EMA_signal_range))
            for ema_s, ema_m, ema_signal in tqdm(combinations):
                try:
                    self.macd(ema_s, ema_m, ema_signal, technical, shifting)
                    self.run_backtest()
                    for pair, result in self.backtested_data.items():
                        comb_pair.append(pair)
                        comb_s.append(ema_s)
                        comb_m.append(ema_m)
                        comb_signal.append(ema_signal)
                        comb_creturns.append(result["creturns"][-1])
                        comb_cstrategy.append(result["cstrategy"][-1])

                        self.performance_data = pd.DataFrame(list(zip(comb_pair,
                                                                      comb_s,
                                                                      comb_m,
                                                                      comb_signal,
                                                                      comb_creturns,
                                                                      comb_cstrategy)),
                                                             columns=["Asset",
                                                                      "EMA_S",
                                                                      "EMA_M",
                                                                      "SIGNAL",
                                                                      "creturns",
                                                                      "cstrategy"])
                except Exception as e:
                    print(e)

            self.calculate_performance()
