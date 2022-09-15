from time_operators.time_operator import TimeOperator
from connectors.binanceConnect import BinanceClient

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

plt.style.use("seaborn")


class Backtester(TimeOperator):
    """ Class for the backtesting simple trading strategies """

    def __init__(self,
                 key: str,
                 secret: str,
                 use_testnet: bool,
                 interval: str,
                 start: int,
                 symbols: list,
                 tc: float,
                 period_cagr="month"):
        self.symbols = symbols
        self.api_key = key
        self.api_secret = secret
        self.use_testnet = use_testnet
        self.interval = interval
        self.period_cagr = period_cagr
        self.start = start
        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d",
                                    "1w", "1M"]
        self.tc = tc
        self.results = {}
        self.time = TimeOperator()
        self.client = BinanceClient(self.api_key, self.api_secret, self.use_testnet)
        self.performance_data = pd.DataFrame
        self.data = self.prepare_data()
        self.cstrategy_data = []
        self.tp = self.calculate_tp(self.period_cagr)

    def calculate_tp(self, period="month") -> dict:
        """Calculating trading periods"""

        tp = {}
        if period == "month":
            for pair, data in self.data.items():
                counts = data.Close.count()
                tp[pair] = counts / (data.index[-1] - data.index[0]).days / 30.44
        elif period == "year":
            for pair, data in self.data.items():
                counts = data.Close.count()
                tp[pair] = counts / (data.index[-1] - data.index[0]).days / 365.25
        elif period == "day":
            for pair, data in self.data.items():
                counts = data.Close.count()
                tp[pair] = counts / (data.index[-1] - data.index[0]).days / 1
        else:
            print("Wrong period chosen!")

        return tp

    def dict_to_json(self, data: dict):
        return json.dumps(data)

    def dataframe_to_json(self, data: pd.DataFrame, orient="records", lines=True):
        dict_data = data.to_dict()
        return self.dict_to_json(dict_data)

    def fetch_data(self, period: str, symbol: str):
        """ Fetching the historic data from Binance """
        if period in self.available_intervals:
            raw = self.client.get_historicals(symbol=symbol,
                                              period=period,
                                              start=self.start,
                                              end=self.time.generate_current_timestamp())
            return raw

    def prepare_data(self, drop_columns=False) -> dict:
        """ Imports the data, and prepare for testing."""

        print(
            f"Fetching a data for backtesting of {len(self.symbols)} symbols with INTERVAL: {self.interval} and START: {self.start}")
        self.data = {}
        for symbol in self.symbols:
            raw = self.fetch_data(self.interval, symbol)
            df = raw.copy()
            if drop_columns:
                df.drop(columns=["Open", "High", "Low", "Volume", "Complete"], inplace=True)
            df["returns"] = np.log(df.Close.div(df.Close.shift(1)))
            df.dropna(inplace=True)
            self.data[symbol] = df

        return self.data.copy()

    def backtest(self, to_backtest_data):
        """ Calculate backtest scores """

        backtested = {}

        for pairs, data in to_backtest_data.items():
            data.copy().dropna(inplace=True)
            data["strategy"] = data["position"].shift(1) * data["returns"]
            data["trades"] = data.position.diff().fillna(0).abs()
            data.strategy = data.strategy + data.trades * self.tc
            data.dropna(inplace=True)

            backtested[pairs] = data

        return backtested

    def test_strategy(self, test_data):
        results_data = {}
        backtested_data = self.backtest(test_data)
        for pairs, data in backtested_data.items():
            data["creturns"] = data["returns"].cumsum().apply(np.exp)
            data["cstrategy"] = data["strategy"].cumsum().apply(np.exp)
            data.dropna(inplace=True)

            results_data[pairs] = data
        return results_data

    def plot_performance(self):
        if self.results is not None:
            for pairs, result in self.results.items():
                result[["creturns", "cstrategy"]].plot(title=f"{pairs} performance")
            plt.show()
        else:
            print("Run first backtest. There's no result data.")

    def measure_performance(self, cagr=True):
        """ Calculates and prints various Performance Metrics."""
        performance_df = pd.DataFrame(columns=["Asset",
                                               "Multiple_Strategy",
                                               "Multiple_Hodl",
                                               "Percent_of_increase_Strategy",
                                               "Percent_of_increase_Hodl",
                                               "Out_Underperformed",
                                               "CAGR",
                                               "Percent_ANN_mean",
                                               "Percent_ANN_std"])
        columns = list(performance_df)
        pf_data = []

        for pairs, result in self.results.items():
            data = result
            strategy_multiple = round(self.calculate_multiple(data.strategy), 9)
            strategy_multiple_percentage = round((strategy_multiple - 1) * 100, 3)
            bh_multiple = round(self.calculate_multiple(data.returns), 9)
            bh_multiple_percentage = round((bh_multiple - 1) * 100, 2)
            outperf = round(strategy_multiple - bh_multiple, 9)
            cagr = round(self.calculate_cagr(data.strategy), 9)
            ann_mean = round(round(self.calculate_annualized_mean(data.strategy, pairs), 8) * 100, 9)
            ann_std = round(round(self.calculate_annualized_std(data.strategy, pairs), 8) * 100, 9)

            values = [pairs,
                      strategy_multiple,
                      bh_multiple,
                      strategy_multiple_percentage,
                      bh_multiple_percentage,
                      outperf,
                      cagr,
                      ann_mean,
                      ann_std]
            zipped = zip(columns, values)
            data_dict = dict(zipped)
            pf_data.append(data_dict)

        self.performance_data = performance_df.append(pf_data, True)
        return self.dataframe_to_json(self.performance_data)

    def print_performance(self):
        for pairs, result in self.results.items():
            data = result
            strategy_multiple = round(self.calculate_multiple(data.strategy), 9)
            bh_multiple = round(self.calculate_multiple(data.returns), 9)
            outperf = round(strategy_multiple - bh_multiple, 9)
            cagr = round(self.calculate_cagr(data.strategy), 4)
            ann_mean = round(self.calculate_annualized_mean(data.strategy, pairs), 9)
            ann_std = round(self.calculate_annualized_std(data.strategy, pairs), 9)

            print(100 * "=")
            print("SIMPLE PRICE & VOLUME STRATEGY | INSTRUMENT :       {} ".format(pairs, 5))
            print(100 * "-")
            print("PERFORMANCE MEASURES:")
            print("\n")
            print("Multiple (Strategy):                                {}".format(strategy_multiple))
            print("Multiple (Buy-and-Hold):                            {}".format(bh_multiple))
            print("Percent of increase (Strategy):                     {}%".format(round((strategy_multiple - 1) * 100),
                                                                                   2))
            print("Percent of increase (Buy-and-Hold):                 {}%".format(round((bh_multiple - 1) * 100), 2))
            print(38 * "-")
            print("Out-/Underperformance:                              {}".format(round(outperf * 100, 2)))
            print("CAGR :                                              {}%    (period: {})".format(round(cagr * 100, 2),
                                                                                                   self.period_cagr))
            print("Annualized Mean (MEAN REWARD):                      {}".format(round(ann_mean * 100, 6)))
            print("Annualized Std (RISK POSITION):                     {}".format(round(ann_std * 100, 6)))
            print(100 * "=")
            print("\n")

    def calculate_multiple(self, series):
        return np.exp(series.sum())

    def calculate_cagr(self, series):
        try:
            if self.period_cagr == "year":
                return np.exp(series.sum()) ** (1 / ((series.index[-1] - series.index[0]).days / 365.25)) - 1
            elif self.period_cagr == "month":
                return np.exp(series.sum()) ** (1 / ((series.index[-1] - series.index[0]).days / 30.44)) - 1
            elif self.period_cagr == "day":
                return np.exp(series.sum()) ** (1 / ((series.index[-1] - series.index[0]).days / 1)) - 1
        except Exception as e:
            print(e)

    def calculate_annualized_mean(self, series, pair):
        return series.mean() * self.tp[pair]

    def calculate_annualized_std(self, series, pair):
        return series.std() * np.sqrt(self.tp[pair])
