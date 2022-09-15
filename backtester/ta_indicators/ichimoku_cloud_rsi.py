import pandas as pd
from backtester.model.backtester import Backtester
from strategies.ta_indicators.ichimoku_cloud_rsi import IchimokuCloudRSIStrategy
from exit_rules.backtesting_exit_rules import ExitRules

from tqdm import tqdm
import copy
from itertools import product


class IchimokuCloudRSI:
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
        self.ichimoku_data = {}
        self.backtested_data = {}
        self.strategy = strategy
        self.performance_data = pd.DataFrame

    def ichimoku_cloud_rsi(self,
                           conversion_window=9,
                           base_window=26,
                           span_window=52,
                           leading_shift=26,
                           lagging_shift=26,
                           # RSI
                           rsi_window=14,
                           # EMA
                           ema_window=200,
                           # STOP LOSS Parameters
                           stop_loss=1.5,
                           atr_window=14,
                           atr_stop_loss=True,
                           fixed_stop_loss=False,
                           trailing_stop_loss=False,
                           ema_calc=True,
                           own_smoothing=False):
        new_data = copy.deepcopy(self.backtester.data)

        for pairs, data in new_data.items():

            strategy = IchimokuCloudRSIStrategy(data)
            self.ichimoku_data[pairs] = strategy.ichimoku_cloud_rsi(
                conversion_window=conversion_window,
                base_window=base_window,
                span_window=span_window,
                leading_shift=leading_shift,
                lagging_shift=lagging_shift,
                rsi_window=rsi_window,
                ema_window=ema_window
            )

            if fixed_stop_loss and not trailing_stop_loss and not atr_stop_loss:
                self.ichimoku_data[pairs] = ExitRules(data).fixed_stop_loss(stop_loss)

            elif trailing_stop_loss and not fixed_stop_loss and not atr_stop_loss:
                self.ichimoku_data[pairs] = ExitRules(data).trailing_stop_loss(stop_loss)

            elif atr_stop_loss and not fixed_stop_loss and not trailing_stop_loss:
                self.ichimoku_data[pairs] = ExitRules(data).atr_stop_loss(window=atr_window,
                                                                          stop_loss=stop_loss,
                                                                          ema_calc=ema_calc,
                                                                          own_smoothing=own_smoothing)

    def run_backtest(self):
        if self.ichimoku_data is None:
            print("Implement strategy firstly.")
        else:
            self.backtested_data = self.backtester.test_strategy(self.ichimoku_data)
            return self.backtested_data

    def measure_performance(self, print_performance=False, plot_performance=False):
        if self.backtested_data is not None:
            self.backtester.results = copy.deepcopy(self.backtested_data)
            scores = self.backtester.measure_performance()
            if print_performance:
                self.backtester.print_performance()
            if plot_performance:
                self.backtester.plot_performance()
            return scores
        else:
            print("There's no backtested data.")

    def calculate_performance(self) -> dict:
        if self.strategy == "ichimoku_cloud_rsi":
            scores = {}
            assets = self.performance_data["Asset"].unique()

            for asset in assets:
                indexes = self.performance_data[self.performance_data["Asset"] == asset]["cstrategy"].nlargest(
                    3).index.values
                conversion_window = []
                base_window = []
                span_window = []
                leading_shift = []
                lagging_shift = []
                rsi_window = []
                ema_window = []
                stop_loss = []
                atr_window = []
                atr_stop_loss = []
                fixed_stop_loss = []
                trailing_stop_loss = []
                ema_calc = []
                own_smoothing = []
                creturns = []
                cstrategy = []

                for idx in indexes:
                    conversion_window.append(float(self.performance_data["Conversation_window"].iloc[int(idx)]))
                    base_window.append(float(self.performance_data["Base_window"].iloc[int(idx)]))
                    span_window.append(float(self.performance_data["Span_window"].iloc[int(idx)]))
                    leading_shift.append(float(self.performance_data["Leading_shift"].iloc[int(idx)]))
                    lagging_shift.append(float(self.performance_data["Lagging_shift"].iloc[int(idx)]))
                    rsi_window.append(float(self.performance_data["Rsi_window"].iloc[int(idx)]))
                    ema_window.append(float(self.performance_data["Ema_window"].iloc[int(idx)]))
                    stop_loss.append(str(self.performance_data["Stop_loss"].iloc[int(idx)]))
                    atr_window.append(str(self.performance_data["Atr_window"].iloc[int(idx)]))
                    atr_stop_loss.append(str(self.performance_data["Atr_stop_loss"].iloc[int(idx)]))
                    fixed_stop_loss.append(str(self.performance_data["Fixed_stop_loss"].iloc[int(idx)]))
                    trailing_stop_loss.append(str(self.performance_data["Trailing_stop_loss"].iloc[int(idx)]))
                    ema_calc.append(str(self.performance_data["Ema_calc"].iloc[int(idx)]))
                    own_smoothing.append(str(self.performance_data["Own_smoothing"].iloc[int(idx)]))
                    creturns.append(float(self.performance_data["creturns"].iloc[int(idx)]))
                    cstrategy.append(float(self.performance_data["cstrategy"].iloc[int(idx)]))
                scores[asset] = [{"Conversation_window": conversion_window},
                                 {"Base_window": base_window},
                                 {"Span_window": span_window},
                                 {"Leading_shift": leading_shift},
                                 {"Lagging_shift": lagging_shift},
                                 {"Rsi_window": rsi_window},
                                 {"Ema_window": ema_window},
                                 {"Stop_loss": stop_loss},
                                 {"Atr_window": atr_window},
                                 {"Atr_stop_loss": atr_stop_loss},
                                 {"Fixed_stop_loss": fixed_stop_loss},
                                 {"Trailing_stop_loss": trailing_stop_loss},
                                 {"Ema_calc": ema_calc},
                                 {"Own_smoothing": own_smoothing},
                                 {"creturns": creturns},
                                 {"cstrategy": cstrategy}]

            print(scores)
            return self.backtester.dict_to_json(scores)

    def all_combinantion(self,
                         conversion_window_range=None,
                         base_window_range=None,
                         span_window_range=None,
                         leading_shift_range=None,
                         lagging_shift_range=None,
                         rsi_window=14,
                         ema_window=200,
                         stop_loss=1.5,
                         atr_window=14,
                         atr_stop_loss=True,
                         fixed_stop_loss=False,
                         trailing_stop_loss=False,
                         ema_calc=True,
                         own_smoothing=False
                         ):

        comb_creturns = []
        comb_cstrategy = []
        comb_pair = []
        comb_conversion_window = []
        comb_base_window = []
        comb_span_window = []
        comb_leading_shift = []
        comb_lagging_shift = []
        comb_rsi_window = []
        comb_ema_window = []
        comb_stop_loss = []
        comb_atr_window = []
        comb_atr_stop_loss = []
        comb_fixed_stop_loss = []
        comb_trailing_stop_loss = []
        comb_ema_calc = []
        comb_own_smoothing = []

        if self.strategy == "ichimoku_cloud_rsi":

            combinations = list(product(conversion_window_range,
                                        base_window_range,
                                        span_window_range,
                                        leading_shift_range,
                                        lagging_shift_range))
            for conv_range, base_wid, span_wid, lead_shift, lag_shift in tqdm(combinations):
                try:
                    self.ichimoku_cloud_rsi(conversion_window=conv_range,
                                            base_window=base_wid,
                                            span_window=span_wid,
                                            leading_shift=lead_shift,
                                            lagging_shift=lag_shift,
                                            rsi_window=rsi_window,
                                            ema_window=ema_window,
                                            stop_loss=stop_loss,
                                            atr_window=atr_window,
                                            atr_stop_loss=atr_stop_loss,
                                            fixed_stop_loss=fixed_stop_loss,
                                            trailing_stop_loss=trailing_stop_loss,
                                            ema_calc=ema_calc,
                                            own_smoothing=own_smoothing
                                            )
                    self.run_backtest()
                    for pair, result in self.backtested_data.items():
                        comb_pair.append(pair)
                        comb_conversion_window.append(conv_range)
                        comb_base_window.append(base_wid)
                        comb_span_window.append(span_wid)
                        comb_leading_shift.append(lead_shift)
                        comb_lagging_shift.append(lag_shift)
                        comb_rsi_window.append(rsi_window)
                        comb_ema_window.append(ema_window)
                        comb_stop_loss.append(stop_loss)
                        comb_atr_window.append(atr_window)
                        comb_atr_stop_loss.append(atr_stop_loss)
                        comb_fixed_stop_loss.append(fixed_stop_loss)
                        comb_trailing_stop_loss.append(trailing_stop_loss)
                        comb_ema_calc.append(ema_calc)
                        comb_own_smoothing.append(own_smoothing)
                        comb_creturns.append(result["creturns"][-1])
                        comb_cstrategy.append(result["cstrategy"][-1])

                        self.performance_data = pd.DataFrame(list(zip(comb_pair,
                                                                      comb_conversion_window,
                                                                      comb_base_window,
                                                                      comb_span_window,
                                                                      comb_leading_shift,
                                                                      comb_lagging_shift,
                                                                      comb_rsi_window,
                                                                      comb_ema_window,
                                                                      comb_stop_loss,
                                                                      comb_atr_window,
                                                                      comb_atr_stop_loss,
                                                                      comb_fixed_stop_loss,
                                                                      comb_trailing_stop_loss,
                                                                      comb_ema_calc,
                                                                      comb_own_smoothing,
                                                                      comb_creturns,
                                                                      comb_cstrategy)),
                                                             columns=["Asset",
                                                                      "Conversation_window",
                                                                      "Base_window",
                                                                      "Span_window",
                                                                      "Leading_shift",
                                                                      "Lagging_shift",
                                                                      "Rsi_window",
                                                                      "Ema_window",
                                                                      "Stop_loss",
                                                                      "Atr_window",
                                                                      "Atr_stop_loss",
                                                                      "Fixed_stop_loss",
                                                                      "Trailing_stop_loss",
                                                                      "Ema_calc",
                                                                      "Own_smoothing",
                                                                      "creturns",
                                                                      "cstrategy"])
                except Exception as e:
                    print(e)

            self.calculate_performance()
