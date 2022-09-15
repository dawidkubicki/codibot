import pandas as pd
import time
import numpy as np
import os
import threading
import json

from connectors.binanceConnect import BinanceClient
from time_operators.time_operator import TimeOperator

from strategies.ta_indicators.macd import MACDStrategy

from exit_rules.trading_exit_rules import ExitRules


class MACDCrossoverBOT(BinanceClient, TimeOperator):
    def __init__(self,
                 key: str,
                 secret: str,
                 use_testnet: bool,
                 base_symbol: str,
                 quote_symbol: str,
                 bar_length: str,
                 strategy_type: str,
                 units: float,
                 position=0,
                 market_order_type="quantity",
                 trades_limit=100,
                 exit_trade_delay=1,

                 # STOP-LOSS
                 fixed_stop_loss=False,
                 trailing_stop_loss=False,
                 atr_stop_loss=True,
                 atr_stop_loss_window=14,
                 atr_stop_loss_own_smoothing=False,
                 stop_loss=1.5,

                 # TAKE PROFIT
                 take_profit=1.05,

                 # MACD Strategy
                 ema_s_macd=None,
                 ema_m_macd=None,
                 ema_signal_macd=None,
                 technical_macd=True,
                 shifting_macd=False,

                 ):
        """
        :param strategy_type: "params here to be added"
        """
        self.api_key = key
        self.api_secret = secret
        self.use_testnet = use_testnet
        self.client = BinanceClient(self.api_key, self.api_secret, self.use_testnet)
        self.time = TimeOperator()
        self.base_symbol = base_symbol
        self.quote_symbol = quote_symbol
        self.symbol = str(base_symbol).upper() + str(quote_symbol).upper()
        self.bar_length = bar_length
        self.strategy_type = strategy_type

        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d",
                                    "1w", "1M"]
        self.units = units
        self.market_order_type = market_order_type
        self.position = position
        self.exit_trade_delay = exit_trade_delay
        self.exit_activated_long = False
        self.exit_activated_short = False
        self.trades = 0
        self.trade_values = []

        self.data = pd.DataFrame()
        self.trades_limit = trades_limit
        self.buying_price = 0
        self.selling_price = 0
        self.ST_long_price = 0
        self.ST_short_price = 0
        self.TP_long_price = 0
        self.TP_short_price = 0
        self.trailing_stop_loss_prices = pd.DataFrame(columns=['Price'])
        self.trailing_stop_loss_long = pd.DataFrame(columns=['ST_long_price'])
        self.trailing_stop_loss_short = pd.DataFrame(columns=['ST_short_price'])
        self.ws = None
        self.prepared_data = None

        # STOP LOSS
        self.stop_loss = stop_loss
        self.fixed_stop_loss = fixed_stop_loss
        self.trailing_stop_loss = trailing_stop_loss
        self.atr_stop_loss = atr_stop_loss
        self.atr_stop_loss_window = atr_stop_loss_window
        self.atr_stop_loss_own_smoothing = atr_stop_loss_own_smoothing

        # TAKE PROFIT
        self.take_profit = take_profit

        # MACD Strategy
        self.ema_s_macd = ema_s_macd
        self.ema_m_macd = ema_m_macd
        self.ema_signal_macd = ema_signal_macd
        self.technical_macd = technical_macd
        self.shifting_macd = shifting_macd

    def get_historical_klines(self, symbol: str, period: str, start: int, end=None, dataframe=True, limit=1000,
                              logs=False):
        """
        Return a DataFrame or a List of historical candlesticks of a chosen asset
        """
        return self.client.get_historicals(symbol, period, start, end, dataframe, limit, logs)

    def save_balances(self):
        """
        Save to a CSV file account balances
        """
        print(f"Current balance: {self.client.get_account_balance()}")
        assets, amounts = [], []
        for asset, amount in self.client.get_account_balance().items():
            assets.append(asset)
            amounts.append(amount)

        date = self.time.generate_current_timestamp()
        outname = f"{date}-{self.symbol}-balance.csv"
        outdir = "./balances"

        if not os.path.exists(outdir):
            os.mkdir(outdir)

        fullname = os.path.join(outdir, outname)

        df = pd.DataFrame(list(zip(assets, amounts)), columns=["Asset", "Balance"])
        df.to_csv(fullname, index=False)

    def get_most_recent(self, symbol, interval, days):
        """
        Return as self.data a historical data
        """
        start_str = self.time.generate_reverse_days(days)
        print(f"Fetching historical data of symbol: {symbol}, interval: {interval}, of last {days} days...")
        self.data = self.get_historical_klines(symbol=symbol, period=interval, start=start_str,
                                               end=self.time.generate_current_timestamp())

    def on_kline_stream(self, ws, msg):
        data = json.loads(msg)

        if "e" in data:

            start_time = pd.to_datetime(data['k']['t'], unit="ms")
            open = float(data['k']['o'])
            high = float(data['k']['h'])
            low = float(data['k']['l'])
            close = float(data['k']['c'])
            volume = float(data['k']['v'])
            complete = data['k']['x']

            # stop trading session
            if self.trades >= self.trades_limit:  # stop stream after trades limit
                self.client.ws.close()
                # self.save_balances()
                if self.position == 1:
                    order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                                   amount=self.units, quantity_type=self.market_order_type)
                    self.report_trade(order, "GOING NEUTRAL AND STOP")
                    self.position = 0
                elif self.position == -1:
                    order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                                  amount=self.units, quantity_type=self.market_order_type)
                    self.report_trade(order, "GOING NEUTRAL AND STOP")
                    self.position = 0
                else:
                    print("STOP")

            # Feed self.data historic data with websocket data (add new bar / update latest bar)
            self.data.loc[start_time] = [open, high, low, close, volume, complete]
            print(f"Last Close price of {self.symbol} : {self.data['Close'].iloc[-1]} | Position: {self.position}")

            # Prepare features and define strategy/trading positions whenever the latest bar is complete
            if complete:
                self.define_strategy()
                self.execute_trades()
                self.exit_trades()

    def exit_strategy(self,
                      data: pd.DataFrame,
                      long_price=0.0,
                      short_price=0.0,
                      last_price=pd.DataFrame(),
                      sl_long=pd.DataFrame(),
                      sl_short=pd.DataFrame(), ):

        # Initialize ExitRules object
        exit_rule_instance = ExitRules(data)

        # Fixed Stop Loss
        if self.fixed_stop_loss and not self.trailing_stop_loss and not self.atr_stop_loss:
            data = exit_rule_instance.fixed_stop_loss(stop_loss=self.stop_loss,
                                                      long_price=long_price,
                                                      short_price=short_price)

        # Trailing Stop Loss
        elif self.trailing_stop_loss and not self.fixed_stop_loss and not self.atr_stop_loss:
            data = exit_rule_instance.trailing_stop_loss(stop_loss=self.stop_loss,
                                                         long_price=long_price,
                                                         short_price=short_price,
                                                         last_price=last_price,
                                                         sl_long=sl_long,
                                                         sl_short=sl_short)

        # ATR Stop Loss
        elif self.atr_stop_loss and not self.fixed_stop_loss and not self.trailing_stop_loss:
            data = exit_rule_instance.atr_stop_loss(window=self.atr_stop_loss_window,
                                                    stop_loss=self.stop_loss,
                                                    own_smoothing=self.atr_stop_loss_own_smoothing,
                                                    last_price=last_price,
                                                    sl_long=sl_long,
                                                    sl_short=sl_short)

        # Take Profit
        if self.take_profit is not None:
            data = exit_rule_instance.fixed_take_profit(take_profit=self.take_profit,
                                                        long_price=long_price,
                                                        short_price=short_price)

        return data

    def define_strategy(self):
        data = self.data.copy()

        if self.strategy_type == "macd":
            # Strategy
            trading_strategy = MACDStrategy(data)
            data = trading_strategy.macd(ema_s=self.ema_s_macd,
                                         ema_m=self.ema_m_macd,
                                         ema_signal=self.ema_signal_macd,
                                         technical=self.technical_macd,
                                         shifting=self.shifting_macd)

        else:
            print("Wrong strategy chosen.")
            ValueError()

        self.prepared_data = data

    def exit_trades(self):
        try:
            if self.prepared_data is not None:
                data = self.prepared_data.copy()

                # Long position from strategy
                if self.position == 1:  # if position is long

                    # Implement exit strategy
                    exit_data = self.exit_strategy(data=data,
                                                   long_price=self.buying_price,
                                                   last_price=self.trailing_stop_loss_prices,
                                                   sl_long=self.trailing_stop_loss_long,
                                                   sl_short=self.trailing_stop_loss_short)

                    # Save to variable current STOP Loss price
                    self.ST_long_price = exit_data['ST_long_price'].iloc[-1]

                    print(f"============================================\n"
                          f"Long STOP LOSS set to: {round(self.ST_long_price, 2)}\n"
                          f"")

                    # If Trailing Stop Loss chosen update DataFrame
                    if self.trailing_stop_loss or self.atr_stop_loss:
                        new_row = {'Price': self.data.Close.iloc[-1]}
                        self.trailing_stop_loss_prices = self.trailing_stop_loss_prices.append(new_row,
                                                                                               ignore_index=True)

                        long_row = {'ST_long_price': self.ST_long_price}
                        self.trailing_stop_loss_long = self.trailing_stop_loss_long.append(long_row, ignore_index=True)

                        print(self.trailing_stop_loss_prices)
                    # Check if Stop Loss has been activated
                    if exit_data["ST_long_active"].iloc[-1] == 1:

                        # Make a sell order
                        order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                                       amount=self.units, quantity_type=self.market_order_type)
                        # Report trade
                        self.report_trade(order,
                                          f"STOP LOSS activated with SL Price: {round(exit_data['ST_long_price'].iloc[-1], 2)} "
                                          f"GOING NEUTRAL FROM LONG")

                        # Set position to 0
                        self.position = 0

                        # Reset trailing DataFrame if needed
                        if self.trailing_stop_loss or self.atr_stop_loss:
                            self.trailing_stop_loss_prices = pd.DataFrame(columns=['Price'])
                            self.trailing_stop_loss_long = pd.DataFrame(columns=['ST_long_price'])

                        # Set reverse strategy await
                        self.exit_activated_long = True

                    # Update Take Profit price
                    self.TP_long_price = exit_data['TP_long_price'].iloc[-1]

                    print(f""
                          f"Long TAKE PROFIT set to: {round(self.TP_long_price, 2)}\n"
                          f"============================================\n")

                    # Check if Take Profit has been activated
                    if exit_data['TP_long_active'].iloc[-1] == 1:
                        # Make a sell order
                        order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                                       amount=self.units, quantity_type=self.market_order_type)
                        # Report trade
                        self.report_trade(order,
                                          f"TAKE PROFIT activated with TP Price: {round(exit_data['TP_long_price'].iloc[-1], 2)} "
                                          f"GOING NEUTRAL")

                        # Set position to 0
                        self.position = 0

                        # Set reverse strategy await
                        self.exit_activated_long = True

                # Short position from strategy
                if self.position == -1:  # if position is short

                    # Implement exit strategy
                    exit_data = self.exit_strategy(data=data,
                                                   short_price=self.selling_price,
                                                   last_price=self.trailing_stop_loss_prices,
                                                   sl_long=self.trailing_stop_loss_long,
                                                   sl_short=self.trailing_stop_loss_short)

                    self.ST_short_price = exit_data['ST_short_price'].iloc[-1]

                    print(f"============================================\n"
                          f"Short STOP LOSS set to: {round(self.ST_short_price, 2)}\n"
                          f"")

                    # If Trailing Stop Loss chosen update DataFrame
                    if self.trailing_stop_loss or self.atr_stop_loss:
                        new_row = {'Price': self.data.Close.iloc[-1]}
                        self.trailing_stop_loss_prices = self.trailing_stop_loss_prices.append(new_row,
                                                                                               ignore_index=True)

                        short_row = {'ST_short_price': self.ST_short_price}
                        self.trailing_stop_loss_short = self.trailing_stop_loss_short.append(short_row,
                                                                                             ignore_index=True)

                    # Check if Stop Loss has been activated
                    if exit_data["ST_short_active"].iloc[-1] == 1:
                        # Make a buy order
                        order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                                      amount=self.units, quantity_type=self.market_order_type)

                        # Report trade
                        self.report_trade(order,
                                          f"STOP LOSS activated with SL Price: {round(exit_data['ST_short_price'].iloc[-1], 2)} "
                                          f"GOING NEUTRAL FROM SHORT")

                        # Set position to 0
                        self.position = 0

                        # Reset trailing DataFrame if needed
                        if self.trailing_stop_loss or self.atr_stop_loss:
                            self.trailing_stop_loss_prices = pd.DataFrame(columns=['Price'])
                            self.trailing_stop_loss_short = pd.DataFrame(columns=['ST_short_price'])
                            self.trailing_stop_loss_long = pd.DataFrame(columns=['ST_long_price'])

                        # Set reverse strategy await
                        self.exit_activated_short = True

                    # Update Take Profit
                    self.TP_short_price = exit_data['TP_short_price'].iloc[-1]

                    print(f""
                          f"Short TAKE PROFIT set to: {round(self.TP_short_price, 2)}\n"
                          f"\n============================================")

                    # Check if Take Profit activated
                    if exit_data["TP_short_active"].iloc[-1] == 1:
                        # Make a buy order
                        order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                                      amount=self.units, quantity_type=self.market_order_type)

                        # Report trade
                        self.report_trade(order,
                                          f"TAKE PROFIT activated with TP Price: {round(exit_data['TP_short_price'].iloc[-1], 2)} "
                                          f"GOING NEUTRAL")

                        # Set position to 0
                        self.position = 0

                        # Set reverse strategy await
                        self.exit_activated_short = True

        except Exception as e:
            print(f"Exit trade error with exception: {e}")

    def execute_trades(self):
        # Long position from strategy
        if self.prepared_data["position"].iloc[-1] == 1:  # if position is long -> go/stay long

            # Reset short position exit reverse
            self.exit_activated_short = False

            # If exit trade activated during long position, wait for reversal
            if not self.exit_activated_long:

                if self.position == 0:
                    # Make a buy order
                    order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                                  amount=self.units, quantity_type=self.market_order_type)
                    # Set a buying price
                    self.buying_price = self.get_order_price(order)

                    # Report trade
                    self.report_trade(order, "GOING LONG")

                elif self.position == -1:
                    # Make buy order
                    order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                                  amount=self.units, quantity_type=self.market_order_type)
                    # Report trade
                    self.report_trade(order, "GOING NEUTRAL")
                    time.sleep(1)
                    # Make a buy order
                    order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                                  amount=self.units, quantity_type=self.market_order_type)
                    # Set a buying price
                    self.buying_price = self.get_order_price(order)

                    # Report trade
                    self.report_trade(order, "GOING LONG")

                self.position = 1
            else:
                print("Waiting for trend reverse (Exit Trade previously activated).")

                # self.position = 1

        # Neutral position from strategy
        elif self.prepared_data["position"].iloc[-1] == 0:  # if position is neutral -> go/stay neutral

            # Reset short and long position exit reverse
            self.exit_activated_short = False
            self.exit_activated_long = False

            if self.position == 1:
                # Make a sell order
                order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                               amount=self.units, quantity_type=self.market_order_type)
                # Report trade
                self.report_trade(order, "GOING NEUTRAL")

                # Reset trailing DataFrame if needed
                if self.trailing_stop_loss:
                    self.trailing_stop_loss_prices = pd.DataFrame(columns=['Price'])
                    self.trailing_stop_loss_long = pd.DataFrame(columns=['ST_long_price'])
                    self.trailing_stop_loss_short = pd.DataFrame(columns=['ST_short_price'])

            elif self.position == -1:
                # Make a buy order
                order = self.client.buy_order(symbol=self.symbol, side="BUY", type="MARKET",
                                              amount=self.units, quantity_type=self.market_order_type)
                # Report trade
                self.report_trade(order, "GOING NEUTRAL")

                # Reset trailing DataFrame if needed
                if self.trailing_stop_loss:
                    self.trailing_stop_loss_prices = pd.DataFrame(columns=['Price'])
                    self.trailing_stop_loss_long = pd.DataFrame(columns=['ST_long_price'])
                    self.trailing_stop_loss_short = pd.DataFrame(columns=['ST_short_price'])

            self.position = 0

        # Short position from strategy
        if self.prepared_data["position"].iloc[-1] == -1:  # if position is short -> go/stay short

            # Reset long position exit reverse
            self.exit_activated_long = False

            # If exit trade activated during short position, wait for reversal
            if not self.exit_activated_short:

                if self.position == 0:
                    # Make a sell order
                    order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                                   amount=self.units, quantity_type=self.market_order_type)
                    # Set a selling price
                    self.selling_price = self.get_order_price(order)
                    # Report trade
                    self.report_trade(order, "GOING SHORT")
                elif self.position == 1:
                    # Make a sell order
                    order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                                   amount=self.units, quantity_type=self.market_order_type)
                    # Report trade
                    self.report_trade(order, "GOING NEUTRAL")
                    time.sleep(1)
                    # Make a sell order
                    order = self.client.sell_order(symbol=self.symbol, side="SELL", type="MARKET",
                                                   amount=self.units, quantity_type=self.market_order_type)
                    # Set a selling price
                    self.selling_price = self.get_order_price(order)
                    # Report trade
                    self.report_trade(order, "GOING SHORT")

                self.position = -1

            else:
                print("Waiting for trend reverse (Exit Trade previously activated).")
                # self.position = -1

    def get_order_price(self, order) -> float:
        # extract data from order object
        base_units = float(order["executedQty"])
        quote_units = float(order["cummulativeQuoteQty"])
        price = round(quote_units / base_units, 5)

        return price

    def report_trade(self, order, going):

        # extract data from order object
        side = order["side"]
        time = pd.to_datetime(order["transactTime"], unit="ms")
        base_units = float(order["executedQty"])
        quote_units = float(order["cummulativeQuoteQty"])
        price = round(quote_units / base_units, 5)

        # calculate trading profits
        self.trades += 1
        if side == "BUY":
            self.trade_values.append(-quote_units)
        elif side == "SELL":
            self.trade_values.append(quote_units)

        if self.trades % 2 == 0:
            real_profit = round(np.sum(self.trade_values[-2:]), 3)
            self.cum_profits = round(np.sum(self.trade_values), 3)
        else:
            real_profit = 0
            self.cum_profits = round(np.sum(self.trade_values[:-1]), 3)

        # print trade report
        print(2 * "\n" + 100 * "-")
        print("{} | {}".format(time, going))
        print("{} | Base_Units = {} | Quote_Units = {} | Price = {} ".format(time, base_units, quote_units, price))
        print("{} | Profit = {} | CumProfits = {} ".format(time, real_profit, self.cum_profits))
        print(100 * "-" + "\n")

    def get_kline_stream(self, symbol, interval):
        self.client.subscribe_symbol = symbol
        self.client.subscribe_interval = interval

        try:
            t = threading.Thread(target=self.client.start_ws(
                self.client.on_open_kline,
                self.client.on_close,
                self.client.on_error,
                self.on_kline_stream
            ))
            t.start()
        except TimeoutError:
            print("Probably WebSocket connection timed out. Waiting for resuming...")
            time.sleep(2)
            print("Resuming connection...")
            t = threading.Thread(target=self.client.start_ws(
                self.client.on_open_kline,
                self.client.on_close,
                self.client.on_error,
                self.on_kline_stream
            ))
            t.start()

    def start_trading(self, historical_days):
        # self.save_balances()
        if self.bar_length in self.available_intervals:
            self.get_most_recent(symbol=self.symbol, interval=self.bar_length, days=historical_days)
            self.get_kline_stream(self.symbol, self.bar_length)
