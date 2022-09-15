import pandas as pd
from backtester.model.backtester import Backtester
from strategies.ta_indicators.sma import SMAStrategy
from exit_rules.backtesting_exit_rules import ExitRules
from tqdm import tqdm
import copy
from itertools import product


class SMA:
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
        self.sma_data = {}
        self.triple_sma_data = {}
        self.backtested_data = {}
        self.SMA_range = ()
        self.strategy = strategy
        self.performance_data = pd.DataFrame

    def double_sma(self,
                   sma_s: int,
                   sma_l: int,
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

            strategy = SMAStrategy(data=data)
            self.sma_data[pairs] = strategy.double_sma(sma_s, sma_l, technical, shifting)

            if fixed_stop_loss and not trailing_stop_loss and not atr_stop_loss:
                self.sma_data[pairs] = StopLoss(data).fixed_stop_loss(stop_loss)
            elif trailing_stop_loss and not fixed_stop_loss and not atr_stop_loss:
                self.sma_data[pairs] = StopLoss(data).trailing_stop_loss(stop_loss)
            elif atr_stop_loss and not fixed_stop_loss and not trailing_stop_loss:
                self.sma_data[pairs] = StopLoss(data).atr_stop_loss(window=atr_window,
                                                                    stop_loss=stop_loss,
                                                                    ema_calc=ema_calc,
                                                                    own_smoothing=own_smoothing)

    def triple_sma(self,
                   sma_s: int,
                   sma_m: int,
                   sma_l: int,
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

            strategy = SMAStrategy(data=data)
            self.sma_data[pairs] = strategy.triple_sma(sma_s, sma_m, sma_l, technical, shifting)

            if fixed_stop_loss and not trailing_stop_loss and not atr_stop_loss:
                self.sma_data[pairs] = ExitRules(data).fixed_stop_loss(stop_loss)
            elif trailing_stop_loss and not fixed_stop_loss and not atr_stop_loss:
                self.sma_data[pairs] = ExitRules(data).trailing_stop_loss(stop_loss)
            elif atr_stop_loss and not fixed_stop_loss and not trailing_stop_loss:
                self.sma_data[pairs] = ExitRules(data).atr_stop_loss(window=atr_window,
                                                                     stop_loss=stop_loss,
                                                                     ema_calc=ema_calc,
                                                                     own_smoothing=own_smoothing)

    def run_backtest(self):
        if self.sma_data is None:
            print("Implement strategy firstly.")
        else:
            self.backtested_data = self.backtester.test_strategy(self.sma_data)
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
        if self.strategy == "double_sma":
            scores = {}
            assets = self.performance_data["Asset"].unique()

            for asset in assets:
                indexes = self.performance_data[self.performance_data["Asset"] == asset]["cstrategy"].nlargest(
                    3).index.values
                sma_s, sma_l, creturns, cstrategy = [], [], [], []
                for idx in indexes:
                    sma_s.append(int(self.performance_data["SMA_S"].iloc[int(idx)]))
                    sma_l.append(int(self.performance_data["SMA_L"].iloc[int(idx)]))
                    creturns.append(float(self.performance_data["creturns"].iloc[int(idx)]))
                    cstrategy.append(float(self.performance_data["cstrategy"].iloc[int(idx)]))
                scores[asset] = [{"sma_s": sma_s},
                                 {"sma_l": sma_l},
                                 {"creturns": creturns},
                                 {"cstrategy": cstrategy}]

            return self.backtester.dict_to_json(scores)

        elif self.strategy == "triple_sma":

            scores = {}
            assets = self.performance_data["Asset"].unique()

            for asset in assets:
                indexes = self.performance_data[self.performance_data["Asset"] == asset]["cstrategy"].nlargest(
                    3).index.values
                sma_s, sma_l, sma_m, creturns, cstrategy = [], [], [], [], []
                for idx in indexes:
                    sma_s.append(int(self.performance_data["SMA_S"].iloc[int(idx)]))
                    sma_m.append(int(self.performance_data["SMA_M"].iloc[int(idx)]))
                    sma_l.append(int(self.performance_data["SMA_L"].iloc[int(idx)]))
                    creturns.append(float(self.performance_data["creturns"].iloc[int(idx)]))
                    cstrategy.append(float(self.performance_data["cstrategy"].iloc[int(idx)]))
                scores[asset] = [{"sma_s": sma_s},
                                 {"sma_m": sma_m},
                                 {"sma_l": sma_l},
                                 {"creturns": creturns},
                                 {"cstrategy": cstrategy}]

            return self.backtester.dict_to_json(scores)

    def all_combinantion(self, SMA_S_range=None, SMA_M_range=None, SMA_L_range=None, technical=True, shifting=False):

        comb_creturns = []
        comb_cstrategy = []
        comb_pair = []
        comb_s, comb_m, comb_l = [], [], []

        if self.strategy == "double_sma":

            combinations = list(product(SMA_S_range, SMA_L_range))
            for sma_s, sma_l in tqdm(combinations):
                try:
                    self.double_sma(sma_s, sma_l, technical, shifting)
                    self.run_backtest()
                    for pair, result in self.backtested_data.items():
                        comb_pair.append(pair)
                        comb_s.append(sma_s)
                        comb_l.append(sma_l)
                        comb_creturns.append(result["creturns"][-1])
                        comb_cstrategy.append(result["cstrategy"][-1])

                        self.performance_data = pd.DataFrame(list(zip(comb_pair,
                                                                      comb_s,
                                                                      comb_l,
                                                                      comb_creturns,
                                                                      comb_cstrategy)),
                                                             columns=["Asset",
                                                                      "SMA_S",
                                                                      "SMA_L",
                                                                      "creturns",
                                                                      "cstrategy"])
                except Exception as e:
                    print(e)

            self.calculate_performance()

        elif self.strategy == "triple_sma":
            combinations = list(product(SMA_S_range, SMA_M_range, SMA_L_range))
            for sma_s, sma_m, sma_l in tqdm(combinations):
                try:
                    self.triple_sma(sma_s, sma_m, sma_l, technical=technical, shifting=shifting)
                    self.run_backtest()
                    for pair, result in self.backtested_data.items():
                        comb_pair.append(pair)
                        comb_s.append(sma_s)
                        comb_m.append(sma_m)
                        comb_l.append(sma_l)
                        comb_creturns.append(result["creturns"][-1])
                        comb_cstrategy.append(result["cstrategy"][-1])
                        self.performance_data = pd.DataFrame(list(zip(comb_pair,
                                                                      comb_s,
                                                                      comb_m,
                                                                      comb_l,
                                                                      comb_creturns,
                                                                      comb_cstrategy)),
                                                             columns=["Asset",
                                                                      "SMA_S",
                                                                      "SMA_M",
                                                                      "SMA_L",
                                                                      "creturns",
                                                                      "cstrategy"])
                except Exception as e:
                    print(e)
            self.calculate_performance()
