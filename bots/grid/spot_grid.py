import pandas as pd
import time
import threading
import numpy as np
import os
import json
from tqdm import tqdm

from connectors.binanceConnect import BinanceClient
from time_operators.time_operator import TimeOperator
from config import config
from exit_rules.grid_bot_exit_rules import ExitRules


class StaticGridBot(BinanceClient, TimeOperator):
    def __init__(self,
                 key: str,
                 secret: str,
                 use_testnet: bool,
                 base_symbol: str,
                 quote_symbol: str,
                 units: float,
                 fee=0.1,
                 position=0,
                 market_order_type="quantity",
                 trades_limit=100,
                 upper_price=None,
                 lower_price=None,
                 num_grids=None,
                 check_order_freq=2,

                 # STOP-LOSS
                 stop_loss_active=False,
                 stop_loss=30000.0,

                 # TAKE-PROFIT
                 take_profit_active=False,
                 take_profit=50000.0,

                 # STRATEGY
                 grid_line_delay=True,
                 sale_base_asset=True,

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
        self.fee = fee
        self.upper_price = upper_price
        self.lower_price = lower_price
        self.num_grids = num_grids
        self.check_order_freq = check_order_freq

        self.buy_orders_list = []
        self.sell_orders_list = []

        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d",
                                    "1w", "1M"]
        self.units = units
        self.quantity = self.units
        self.market_order_type = market_order_type
        self.position = position
        self.exit_activated_long = False
        self.exit_activated_short = False
        self.trades = 0
        self.trade_values = []

        self.data = pd.DataFrame()
        self.trades_limit = trades_limit
        self.buying_price = 0
        self.selling_price = 0
        self.ws = None
        self.prepared_data = None

        # STOP LOSS
        self.stop_loss_active = stop_loss_active
        self.stop_loss = stop_loss

        # TAKE PROFIT
        self.take_profit_active = take_profit_active
        self.take_profit = take_profit

        # GRID BOT
        self.grid_created = False
        self.current_price = 0.0
        self.grid_width = self.calculate_grid_width()
        self.grid_prices = self.get_grid_prices()
        self.closed_orders_id = []
        self.minimum_required_balance = self.minimum_required_balance()
        self.sale_base_asset = sale_base_asset
        self.filled_sell_orders = []
        self.sell_grid_prices = []
        self.buy_grid_prices = []
        self.starting_quote_balance = round(float(self._get_quote_balance()), config.PRECISION)

    # EXCHANGE METHODS -------------------------------------------------------------------------------------------------

    def _get_base_balance(self) -> float:
        """
        Return a base symbol SPOT wallet balance
        """
        assets_balance = self.client.get_account_balance()
        try:
            for asset, value in assets_balance.items():
                if asset == str(self.base_symbol).upper():
                    return value
        except Exception as e:
            print(f"Error while getting base balance of {e}.")

    def _get_quote_balance(self) -> float:
        """
        Return a quote symbol SPOT wallet balance
        """
        assets_balance = self.client.get_account_balance()
        try:
            for asset, value in assets_balance.items():
                if asset == str(self.quote_symbol).upper():
                    return value
        except Exception as e:
            print(f"Error while getting quote balance of {e}.")

    def _market_limit_order(self, symbol: str, side: str, price: float, quantity: float):
        """
        Create Market Limit Order
        params: symbol="BTCUSDT", side="BUY", price="40000.0", quantity="0.01"
        """
        try:
            order = self.client.sell_order(symbol=symbol,
                                           side=str(side).upper(),
                                           type="LIMIT",
                                           price=price,
                                           amount=quantity,
                                           quantity_type=self.market_order_type)
            return order
        except Exception as e:
            print(f"Error while making a market limit order of {e}.")

    def _check_order_status(self, symbol: str, orderId: int):
        """
        Cheking order of a stutus with symbol and orderId
        params: symbol="BTCUSDT", orderId="12345"
        """
        try:
            order = self.client.get_order_status(symbol=symbol,
                                                 orderId=orderId)
            return order
        except Exception as e:
            print(f"Error while checking order status of: {e}.")

    def _cancel_order(self, symbol: str, orderId: int):
        """
        Canceling order with symbol and orderId
        params: symbol="BTCUSDT", orderId="12345"
        """
        try:
            order = self.client.cancel_order(symbol=symbol,
                                             orderId=orderId)
            return order
        except Exception as e:
            print(f"Error while canceling order of {e}.")

    def _cancel_all_open_orders(self, symbol):
        """
        Cancelling all open orders
        params: symbol="BTCUSDT"
        """
        try:
            order = self.client.cancel_all_orders(symbol=symbol)
            return order
        except Exception as e:
            print(f"Error while cancelling all open orders of: {e}.")

    def _sell_all_base_asset(self):
        pass

    def _get_ticker_price(self, ticker):
        return self.client.get_current_price(tick=ticker)

    # GRID METHODS -----------------------------------------------------------------------------------------------------

    def calculate_grid_width(self) -> float:
        """
        Calculating grid width based on self.upper_price, self.lower_price and self.num_grids
        """
        if self.upper_price > self.lower_price:
            grid_width = float((self.upper_price - self.lower_price) / self.num_grids)
            return round(grid_width, config.PRECISION)
        else:
            print("Upper price of a grid is not greater than lower price.")

    def get_grid_prices(self) -> list:
        """
        Returns a list of prices in range created by upper, lower price and grid width.
        """
        prices = []
        new_price = self.lower_price - self.grid_width

        for i in range(self.num_grids):
            new_price += self.grid_width
            prices.append(round(new_price, config.PRECISION))

        prices.append(round(self.upper_price, config.PRECISION))
        return prices

    def find_closest_price(self, current_price: float, prices: list) -> float:
        """
        Find and return the closest price of grid prices to current close candle price
        """
        return prices[min(range(len(prices)), key=lambda i: abs(prices[i] - current_price))]

    def get_sell_grid_prices(self, closest_price: float, grid_prices: list) -> list:
        """
        Get a list of all sell prices / above current closest price from a grid prices list
        """
        sell_prices = []
        for price in grid_prices:
            if price > closest_price:
                sell_prices.append(price)
        return sell_prices

    def get_buy_grid_prices(self, closest_price: float, grid_prices: list) -> list:
        """
        Get a list of all buy prices / below current closest price from a grid prices list
        """
        buy_prices = []
        for price in grid_prices:
            if price < closest_price:
                buy_prices.append(price)
        return buy_prices

    def quantity_price(self) -> float:
        ticker_price = self.client.get_current_price(self.symbol)
        quantity_price = float(ticker_price) * float(self.quantity)
        return quantity_price

    def minimum_required_balance(self) -> float:
        num_trades = self.num_grids - 1
        quantity_price = self.quantity_price()
        minimum_amount = num_trades * (quantity_price + (quantity_price / 100) * self.fee)
        return minimum_amount

    def is_enough_balance_(self) -> bool:
        try:
            quantity_price = self.quantity_price()
            available_amount = self._get_quote_balance()

            # Minimum trading quantity
            if quantity_price > 10:
                print(f"Avail: {available_amount} Min to fill all buy grids: {self.minimum_required_balance}")
                if float(available_amount) > float(self.minimum_required_balance):
                    return True
                else:
                    print(f"Not enough amount")
                    return False
            else:
                print("Too small quantity")
                return False

        except Exception as e:
            print(f"Error with checking enough balance : {e}.")

    def is_enough_base_to_sell(self) -> bool:
        try:
            num_orders = len(self.sell_grid_prices)
            needed_base_amount = float(self.quantity) * float(num_orders)
            if float(self._get_base_balance()) > float(needed_base_amount):
                return True
            else:
                return False
        except Exception as e:
            print(f"Error while checking enough base to sell : {e}.")

    def create_grid(self):

        if self.is_enough_balance_():
            print("Enough balance :)")
        else:
            print("Not enough balance")

        # amount = self._get_base_balance()
        # print(f"Balance of a {self.base_symbol} : {amount}")

        time.sleep(5)
        if self.current_price >= self.lower_price:

            print(f"Upper price: {self.upper_price}")
            print(f"Lower price: {self.lower_price}")
            print(f"Num grid: {self.num_grids}")
            print(f"Grid prices: {self.grid_prices}")

            closest_price = self.find_closest_price(self.current_price, self.grid_prices)
            print(f"Closest price is: {closest_price}")

            sell_prices = self.get_sell_grid_prices(closest_price, self.grid_prices)
            self.sell_grid_prices = sell_prices
            print(f"SELL PRICES (above): {sell_prices}")

            buy_prices = self.get_buy_grid_prices(closest_price, self.grid_prices)
            self.buy_grid_prices = buy_prices
            print(f"BUY PRICES (below): {buy_prices}")

            quantity_price = self.quantity_price()
            minimum_amount = len(self.buy_grid_prices) * (quantity_price + (quantity_price / 100) * self.fee)
            print(f"Minimum amount of {self.quote_symbol}: {minimum_amount} to fill all buy grids.")

            decision = input(f"Do you want to trade with minimum required amount to trade of {minimum_amount}? (yes / "
                             f"no) : ")

            if decision.lower() == "yes":
                trade_decision = True
            else:
                trade_decision = False

            # Check if there's enough price movement to have at least 1 order
            if len(buy_prices) >= 1 and trade_decision:

                print("PLACING BUY LIMIT ORDERS")
                for buy_price in tqdm(buy_prices):
                    try:
                        buy_order = self._market_limit_order(symbol=self.symbol,
                                                             side="BUY",
                                                             price=buy_price,
                                                             quantity=self.quantity)
                    except Exception as e:
                        print(f"Error while making BUY LIMIT ORDER of {e} Retrying...")
                        continue
                    self.buy_orders_list.append(buy_order)

                enough_base_asset = self.is_enough_base_to_sell()

                if enough_base_asset:
                    print("PLACING SELL LIMIT ORDERS")
                    for sell_price in tqdm(sell_prices):
                        try:
                            sell_order = self._market_limit_order(symbol=self.symbol,
                                                                  side="SELL",
                                                                  price=sell_price,
                                                                  quantity=self.quantity)
                        except Exception as e:
                            print(f"Error while making SELL LIMIT ORDER of {e} Retrying...")
                            continue
                        self.sell_orders_list.append(sell_order)
                else:
                    num_of_needed_sells = len(self.sell_grid_prices)
                    current_base = self._get_base_balance()

                    if float(current_base) > 0:
                        amount_of_possible_sells = int(float(num_of_needed_sells) * float(self.quantity) / float(current_base))
                        if amount_of_possible_sells > 0:
                            i = 1
                            for sell_price in tqdm(sell_prices):
                                try:
                                    if i <= amount_of_possible_sells:
                                        sell_order = self._market_limit_order(symbol=self.symbol,
                                                                              side="SELL",
                                                                              price=sell_price,
                                                                              quantity=self.quantity)
                                        self.sell_orders_list.append(sell_order)
                                        i += 1
                                    else:
                                        print("Can't be place (not enough balance).")

                                except Exception as e:
                                    print(f"Error while making SELL LIMIT ORDER of {e} Retrying...")
                                    continue

                        else:
                            print(f"No sell orders has been filled.")
                    else:
                        print(f"No Base balance.")

                self.grid_created = True

                print(f"BUY ORDERS: {self.buy_orders_list}\n")
                print(f"SELL ORDERS: {self.sell_orders_list}")

            else:
                if not trade_decision:
                    print("Haven't got enough buy orders ")
                    self.grid_created = False
                else:
                    print("I won't trade.")
                    self.grid_created = False

            #
            # time.sleep(5)
            #
            # print("CANCELLING ALL ORDERS")
            # cancellation = self._cancel_all_open_orders(self.symbol)
            # print(cancellation)
        else:
            self.grid_created = False
            print("Current price is out of range.")

    def check_buy_orders(self):
        for idx, buy_order in enumerate(self.buy_orders_list):
            try:
                order = self._check_order_status(self.symbol, int(buy_order["orderId"]))
                order_status = order["status"]
                order_price = order["price"]
                # print(f"Order: {idx+1} of status : {order['status']}")

                if order_status == config.FILLED_ORDER:
                    self.closed_orders_id.append(order["orderId"])
                    print(f"Buy order executed at price: {order_price}")
                    new_sell_price = round((float(order_price) + float(self.grid_width)), config.PRECISION)
                    print(f"Creating new sell order at price: {new_sell_price}")
                    new_sell_order = self._market_limit_order(symbol=self.symbol,
                                                              side=config.SIDE_SELL,
                                                              price=float(new_sell_price),
                                                              quantity=self.quantity)
                    self.sell_orders_list.append(new_sell_order)

                    # print(f"{len(self.buy_orders_list)} BUY ORDERS")
                    # print(f"{len(self.sell_orders_list)} SELL ORDERS")

                    # # Report performance
                    # self.report_trade_performance()

                # print("Updating buy orders list")
                for order_id in self.closed_orders_id:
                    self.buy_orders_list = [buy_order for buy_order in self.buy_orders_list if
                                            buy_order["orderId"] != order_id]
                    # self.sell_orders_list = [sell_order for sell_order in self.sell_orders_list if
                    #                          sell_order["orderId"] != order_id]

            except Exception as e:
                print(f"Checking order status failed with {e}, retrying...")
                continue

    def check_sell_orders(self):
        for idx, sell_order in enumerate(self.sell_orders_list):
            try:
                order = self._check_order_status(self.symbol, int(sell_order["orderId"]))
                order_status = order["status"]
                order_price = order["price"]
                # print(f"Order: {idx+1} of status : {order['status']}")

                if order_status == config.FILLED_ORDER:
                    self.closed_orders_id.append(order["orderId"])
                    self.filled_sell_orders.append(order["orderId"])
                    print(f"Sell order executed at price: {order_price}")
                    new_buy_price = round((float(order_price) - float(self.grid_width)), config.PRECISION)
                    print(f"Creating new buy order at price: {new_buy_price}")
                    new_buy_order = self._market_limit_order(symbol=self.symbol,
                                                             side=config.SIDE_BUY,
                                                             price=float(new_buy_price),
                                                             quantity=self.quantity)
                    self.buy_orders_list.append(new_buy_order)

                    # print(f"{len(self.buy_orders_list)} BUY ORDERS")
                    # print(f"{len(self.sell_orders_list)} SELL ORDERS")
                    # # Report performance
                    # self.report_trade_performance()

                # print("Updating sell orders list")
                for order_id in self.closed_orders_id:
                    self.sell_orders_list = [sell_order for sell_order in self.sell_orders_list if
                                             sell_order["orderId"] != order_id]

            except Exception as e:
                print(f"Checking order status failed with {e}, retrying...")
                continue

    def get_historical_klines(self, symbol: str, period: str, start: int, end=None, dataframe=True, limit=1000,
                              logs=False):
        """
        Return a DataFrame or a List of historical candlesticks of a chosen asset
        """
        return self.client.get_historicals(symbol, period, start, end, dataframe, limit, logs)

    def get_most_recent(self):
        """
        Return as self.data a historical data
        """
        # start_str = self.time.generate_reverse_days(days)
        # print(f"Fetching historical data of symbol: {symbol}, interval: {interval}, of last {days} days...")
        # self.data = self.get_historical_klines(symbol=symbol, period=interval, start=start_str,
        #                                        end=self.time.generate_current_timestamp())
        self.current_price = float(self._get_ticker_price(self.symbol))
        # self.current_price = self.data["Close"].iloc[-1]
        print(f"CURRENT PRICE: {self.current_price}")

        # Create new grid ----------------------------------------------------------------------------------------------
        self.create_grid()

    # Profit Calculations ----------------------------------------------------------------------------------------------

    def grid_profit(self) -> float:

        try:
            # # Fee for one side of a trade
            first_trade_fee = (self.quantity * self.grid_prices[0]) * (self.fee / 100)
            min_grid_profit = self.calculate_grid_width() * self.quantity - first_trade_fee

            return min_grid_profit

        except Exception as e:
            print(f"Error while calculating grid profit of : {e}")

    def unrealized_profit(self):
        try:
            average_buy_price = 0.0
            for buy_price in self.buy_grid_prices:
                average_buy_price += float(buy_price)
            average_buy_price = round(average_buy_price / float(len(self.buy_grid_prices)), config.PRECISION)
            holding_base = float(self._get_base_balance())
            u_profit = (float(self.current_price) - float(average_buy_price)) * holding_base
            return round(float(u_profit), 4)

        except Exception as e:
            print(f"Error while calculating unrealized_profit : {e}.")

    def realized_profit(self):
        try:
            r_profit = float(self.grid_width) * float(self.quantity) * float(len(self.filled_sell_orders))
            return round(float(r_profit), 4)
        except Exception as e:
            print(f"Error while calculating realized_profit : {e}.")

    def total_profit(self):
        try:
            t_profit = float(self.unrealized_profit()) + float(self.realized_profit())
            return round(float(t_profit), 4)
        except Exception as e:
            print(f"Error while calculating total profit : {e}.")

    def report_trade_performance(self):
        unrealized_profit = self.unrealized_profit()
        realized_profit = self.realized_profit()
        total_profit = self.total_profit()
        investment = self.minimum_required_balance

        print(2 * "\n" + 100 * "-")
        print("Investement = {} ".format(investment))
        print("Unrealized Profit = {} | Realized Profit = {} | Total Profit = {} ".format(unrealized_profit,
                                                                                          realized_profit,
                                                                                          total_profit))
        print(100 * "-" + "\n")

    # Exit Rules -------------------------------------------------------------------------------------------------------

    def stop_loss_check(self) -> bool:
        # Stop Loss check
        exit_rule = ExitRules(last_price=self.current_price)
        if exit_rule.stop_price(float(self.stop_loss)):
            print("STOP LOSS hit")
            print("CANCELLING ALL ORDERS")
            cancellation = self._cancel_all_open_orders(self.symbol)
            print(cancellation)

            if self.sale_base_asset:
                print("SELLING ALL THE BASE ASSET")
                amount = self._get_base_balance()
                self.client.sell_order(symbol=self.symbol,
                                       amount=amount)

            return True
        else:
            return False

    def take_profit_check(self) -> bool:
        # Take Profit check
        exit_rule = ExitRules(last_price=self.current_price)
        if exit_rule.take_profit(float(self.take_profit)):
            print("TAKE PROFIT hit")

            print("CANCELLING ALL ORDERS")
            cancellation = self._cancel_all_open_orders(self.symbol)
            print(cancellation)

            return True
        else:
            return False

    # Main trading method ----------------------------------------------------------------------------------------------

    def grid_trading(self):

        print(f"Estimated grid profit is: {self.grid_profit()}")
        print(f"Starting with {self.starting_quote_balance} of {self.quote_symbol}")

        grid_trading_on = True
        trading_active = 0
        while trading_active < 5 and grid_trading_on:
            if self.grid_created:

                checking = True

                self.current_price = float(self._get_ticker_price(self.symbol))

                if self.stop_loss_active:
                    print(f"Checking if STOP LOSS is hit with current price: {self.current_price}")
                    stop_loss_activated = self.stop_loss_check()

                    if stop_loss_activated:
                        checking = False
                        grid_trading_on = False
                        print(f"Grid trading bot stopped due to STOP LOSS HIT PRICE")

                if self.take_profit_active:
                    print(f"Checking if TAKE PROFIT is hit with current price: {self.current_price}")
                    take_profit_activated = self.take_profit_check()

                    if take_profit_activated:
                        checking = False
                        grid_trading_on = False
                        print(f"Grid trading bot stopped due to TAKE PROFIT HIT PRICE")

                if checking:
                    print("Checking buy statuses")
                    self.check_buy_orders()

                    #TODO: Check if use some of the left sell grid orders to fill

                    if len(self.sell_orders_list) > 0:
                        print("Checking sell statuses")
                        self.check_sell_orders()


                    # self.report_trade_performance()

                    checking = False
                    time.sleep(2)

                print(f"{len(self.buy_orders_list)} BUY ORDERS (after update)")
                print(f"{len(self.sell_orders_list)} SELL ORDERS (after update)")

                trading_active += 1

                # print("CANCELLING ALL ORDERS")
                # cancellation = self._cancel_all_open_orders(self.symbol)
                # print(cancellation)
                # trading_active = False

            else:
                self.create_grid()

        print("CANCELLING ALL ORDERS")
        cancellation = self._cancel_all_open_orders(self.symbol)
        print(cancellation)

        print(f"Before grid bot:  {self.starting_quote_balance} of {self.quote_symbol}")
        print(f"After grid bot:  {round(float(self._get_quote_balance()), config.PRECISION)} of {self.quote_symbol}")
        print(
            f"Profit of: {round(float(self._get_quote_balance()) - float(self.starting_quote_balance), config.PRECISION)} : {self.quote_symbol}")

    def start_grid_bot_trading(self):
        self.get_most_recent()
        self.grid_trading()
