import pandas as pd
from backtester.model.backtester import Backtester
from strategies.ta_indicators.sto_rsi_macd import STORSIMACDStrategy
from exit_rules.backtesting_exit_rules import ExitRules
from tqdm import tqdm
import copy
from itertools import product


class STO_RSI_MACD:
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
        self.sto_rsi_macd_data = {}
        self.backtested_data = {}
        self.strategy = strategy
        self.performance_data = pd.DataFrame

    def sto_rsi_macd(self,
                     k_period: int,
                     smoothing_k: int,
                     d_period: int,
                     ema_fast: int,
                     ema_slow: int,
                     ema_sign: int,
                     rsi_window: int,
                     lags: int,
                     shift_position: int,
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
            strategy = STORSIMACDStrategy(data)
            self.sto_rsi_macd_data[pairs] = strategy.sto_rsi_macd(k_period,
                                                                  smoothing_k,
                                                                  d_period,
                                                                  ema_fast,
                                                                  ema_slow,
                                                                  ema_sign,
                                                                  rsi_window,
                                                                  lags,
                                                                  shift_position)

            if fixed_stop_loss and not trailing_stop_loss and not atr_stop_loss:
                self.sto_rsi_macd_data[pairs] = ExitRules(data).fixed_stop_loss(stop_loss)
            elif trailing_stop_loss and not fixed_stop_loss and not atr_stop_loss:
                self.sto_rsi_macd_data[pairs] = ExitRules(data).trailing_stop_loss(stop_loss)
            elif atr_stop_loss and not fixed_stop_loss and not trailing_stop_loss:
                self.sto_rsi_macd_data[pairs] = ExitRules(data).atr_stop_loss(window=atr_window,
                                                                              stop_loss=stop_loss,
                                                                              ema_calc=ema_calc,
                                                                              own_smoothing=own_smoothing)

    def run_backtest(self):
        if self.sto_rsi_macd_data is None:
            print("Implement strategy firstly.")
        else:
            self.backtested_data = self.backtester.test_strategy(self.sto_rsi_macd_data)
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
        if self.strategy == "sto_rsi_macd":
            scores = {}
            assets = self.performance_data["Asset"].unique()

            for asset in assets:
                indexes = self.performance_data[self.performance_data["Asset"] == asset]["cstrategy"].nlargest(
                    3).index.values
                comb_k_period, comb_smoothing_k, comb_d_period, comb_ema_fast, comb_ema_slow, comb_ema_sign, \
                comb_rsi_window, comb_lags, comb_shift_position, creturns, cstrategy = \
                    [], [], [], [], [], [], [], [], [], [], []
                for idx in indexes:
                    comb_k_period.append(int(self.performance_data["k_period"].iloc[int(idx)]))
                    comb_smoothing_k.append(int(self.performance_data["smoothing_k"].iloc[int(idx)]))
                    comb_d_period.append(int(self.performance_data["d_period"].iloc[int(idx)]))
                    comb_ema_fast.append(int(self.performance_data["ema_fast"].iloc[int(idx)]))
                    comb_ema_slow.append(int(self.performance_data["ema_slow"].iloc[int(idx)]))
                    comb_ema_sign.append(int(self.performance_data["ema_sign"].iloc[int(idx)]))
                    comb_rsi_window.append(int(self.performance_data["rsi_window"].iloc[int(idx)]))
                    comb_lags.append(int(self.performance_data["lags"].iloc[int(idx)]))
                    comb_shift_position.append(int(self.performance_data["shit_position"].iloc[int(idx)]))
                    creturns.append(float(self.performance_data["creturns"].iloc[int(idx)]))
                    cstrategy.append(float(self.performance_data["cstrategy"].iloc[int(idx)]))
                scores[asset] = [{"k_period": comb_k_period},
                                 {"smoothing_k": comb_smoothing_k},
                                 {"d_period": comb_d_period},
                                 {"ema_fast": comb_ema_fast},
                                 {"ema_slow": comb_ema_slow},
                                 {"ema_sign": comb_ema_sign},
                                 {"rsi_window": comb_rsi_window},
                                 {"lags": comb_lags},
                                 {"shit_position": comb_shift_position},
                                 {"creturns": creturns},
                                 {"cstrategy": cstrategy}]

            return self.backtester.dict_to_json(scores)

    def all_combinantion(self,
                         k_period_range=None,
                         smoothing_k_range=None,
                         d_period_range=None,
                         ema_fast_range=None,
                         ema_slow_range=None,
                         ema_sign_range=None,
                         rsi_window_range=None,
                         lags_range=None,
                         shift_position_range=None):

        comb_creturns = []
        comb_cstrategy = []
        comb_pair = []
        comb_k_period, comb_smoothing_k, comb_d_period, comb_ema_fast, comb_ema_slow, comb_ema_sign, \
        comb_rsi_window, comb_lags, comb_shift_position = [], [], [], [], [], [], [], [], []

        if self.strategy == "sto_rsi_macd":

            combinations = list(product(k_period_range,
                                        smoothing_k_range,
                                        d_period_range,
                                        ema_fast_range,
                                        ema_slow_range,
                                        ema_sign_range,
                                        rsi_window_range,
                                        lags_range,
                                        shift_position_range
                                        ))
            for k_period, smoothing_k, d_period, ema_fast, ema_slow, ema_sign, rsi_window, lags, shift_position in tqdm(
                    combinations):
                try:
                    self.sto_rsi_macd(k_period, smoothing_k, d_period, ema_fast, ema_slow, ema_sign, rsi_window, lags,
                                      shift_position)
                    self.run_backtest()
                    for pair, result in self.backtested_data.items():
                        comb_pair.append(pair)
                        comb_k_period.append(k_period)
                        comb_smoothing_k.append(smoothing_k)
                        comb_d_period.append(d_period)
                        comb_ema_fast.append(ema_fast)
                        comb_ema_slow.append(ema_slow)
                        comb_ema_sign.append(ema_sign)
                        comb_rsi_window.append(rsi_window)
                        comb_lags.append(lags)
                        comb_shift_position.append(shift_position)
                        comb_creturns.append(result["creturns"][-1])
                        comb_cstrategy.append(result["cstrategy"][-1])

                        self.performance_data = pd.DataFrame(list(zip(comb_pair,
                                                                      comb_k_period,
                                                                      comb_smoothing_k,
                                                                      comb_d_period,
                                                                      comb_ema_fast,
                                                                      comb_ema_slow,
                                                                      comb_ema_sign,
                                                                      comb_rsi_window,
                                                                      comb_lags,
                                                                      comb_shift_position,
                                                                      comb_creturns,
                                                                      comb_cstrategy)),
                                                             columns=["Asset",
                                                                      "k_period",
                                                                      "smoothing_k",
                                                                      "d_period",
                                                                      "ema_fast",
                                                                      "ema_slow",
                                                                      "ema_sign",
                                                                      "rsi_window",
                                                                      "lags",
                                                                      "shift_position",
                                                                      "creturns",
                                                                      "cstrategy"])
                except Exception as e:
                    print(e)

            self.calculate_performance()
