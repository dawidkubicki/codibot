import time
import requests
import pandas as pd
from time_operators.time_operator import TimeOperator
import hmac
import hashlib
from urllib.parse import urlencode

import websocket
import threading
import json


class BinanceClient:
    def __init__(self, public_key, secret_key, testnet=True):
        if testnet:
            self.base_url = "https://testnet.binance.vision"
            self.wss_url = "wss://testnet.binance.vision/ws"
            self.wss_stream_url = "wss://testnet.binance.vision/stream"
        else:
            self.base_url = "https://api.binance.com"
            self.wss_url = "wss://stream.binance.com:9443/ws"
            self.wss_stream_url = "wss://stream.binance.com:9443/stream"

        self.public_key = public_key
        self.secret_key = secret_key
        self.headers = {'X-MBX-APIKEY': self.public_key}

        self.available_intervals = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d",
                                    "1w", "1M"]
        self.time = TimeOperator()

        self.prices = dict()
        self.klines = dict()
        self.ws_id = 1
        self.ws = None

    def generate_signature(self, data):
        """
        :param data: Header for request to API
        :return: Encrypted string
        """
        return hmac.new(self.secret_key.encode(), urlencode(data).encode(), hashlib.sha256).hexdigest()

    def make_request(self, method, endpoint, data=None):
        if method == "GET":
            try:
                response = requests.get(self.base_url + endpoint, params=data, headers=self.headers)
            except Exception as e:
                print(f"Error while making {method} request to: {endpoint}, with data: {data} of: {e}")
        elif method == "POST":
            try:
                response = requests.post(self.base_url + endpoint, params=data, headers=self.headers)
            except Exception as e:
                print(f"Error while making {method} request to: {endpoint}, with data: {data} of: {e}")
        elif method == "DELETE":
            try:
                response = requests.delete(self.base_url + endpoint, params=data, headers=self.headers)
            except Exception as e:
                print(f"Error while making {method} request to: {endpoint}, with data: {data} of: {e}")
        else:
            raise ValueError()

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error while making {method} request to {endpoint} : {response.json()} - status code:"
                  f" {response.status_code}")

    # REST API ---------------------------------------------------------------------------------------------------------

    def get_contracts(self) -> list:
        """
        Returns a list of SPOT/MARGIN (not LEVERAGED) USDT symbols and related to them attributes from Binance API
        """
        exchange_info = self.make_request("GET", "/api/v3/exchangeInfo")
        contracts = list()

        if exchange_info is not None:
            for contract_data in exchange_info['symbols']:
                if "USDT" in str(contract_data['symbol']) and "LEVERAGED" not in str(contract_data['permissions']):
                    contracts.append(contract_data['symbol'])

        return contracts

    def get_historicals(self, symbol: str, period: str, start: int, end=None, dataframe=True, limit=1000, logs=False):
        """
        Returns a DataFrame or a List of historical candlestick of a chosen asset
        """
        if logs:
            print(f"Fetching asset data of symbol: {symbol}, period: {period}, start: {start}, end: {end}")

        candles = []
        if dataframe:
            try:
                current_start = start
                current_end = self.time.period_to_timestamp(current_start, period, limit)
                get_data = 0

                while get_data < 2:
                    params = {
                        "symbol": str(symbol),
                        "interval": str(period),
                        "startTime": int(current_start),
                        "endTime": int(current_end),
                        "limit": int(limit),
                    }

                    if get_data == 1:
                        candle = self.make_request("GET", "/api/v3/klines", params)
                        candles.append(pd.DataFrame(candle))
                        get_data += 1
                        break
                    elif get_data < 2:
                        candle = self.make_request("GET", "/api/v3/klines", params)
                        candles.append(pd.DataFrame(candle))

                    current_start = current_end
                    current_end = self.time.period_to_timestamp(current_start, period, limit)
                    if current_end > end:
                        current_end = end
                        get_data += 1

                columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                           "Clos Time", "Quote Asset Volume", "Number of Trades",
                           "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"]

                df = pd.DataFrame(columns=columns)

                all_res = []
                for s_candle in candles:
                    all_res.append(s_candle)

                df = pd.concat(all_res)
                df["Date"] = pd.to_datetime(df.iloc[:, 0], unit="ms")
                df.columns = ["Open Time", "Open", "High", "Low", "Close", "Volume",
                              "Clos Time", "Quote Asset Volume", "Number of Trades",
                              "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore", "Date"]
                df = df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
                df.set_index("Date", inplace=True)
                for column in df.columns:
                    df[column] = pd.to_numeric(df[column], errors="coerce")
                df["Complete"] = [True for row in range(len(df) - 1)] + [False]
                df.dropna(inplace=True)

                if logs:
                    print(df)

                return df

            except:
                print(f"Could not fetch historic DataFrame of symbol: {symbol}, period: {period}, start: {start}")

        else:
            try:
                current_start = start
                current_end = self.time.period_to_timestamp(current_start, period, limit)
                get_data = 0

                while get_data < 2:
                    params = {
                        "symbol": str(symbol),
                        "interval": str(period),
                        "startTime": int(current_start),
                        "endTime": int(current_end),
                        "limit": int(limit),
                    }

                    if get_data == 1:
                        candle = self.make_request("GET", "/api/v3/klines", params)
                        get_data += 1
                        break
                    elif get_data < 2:
                        candle = self.make_request("GET", "/api/v3/klines", params)

                    current_start = current_end
                    current_end = self.time.period_to_timestamp(current_start, period, limit)
                    if current_end > end:
                        current_end = end
                        get_data += 1

                if logs:
                    print(candles)

                return candles

            except:
                print(f"Could not fetch historic DataFrame of symbol: {symbol}, period: {period}, start: {start}")

    def get_account_details(self):
        """
        Returns a JSON format of a account details
        """

        data = dict()
        data["timestamp"] = self.time.generate_current_timestamp()
        data["signature"] = self.generate_signature(data)

        account = self.make_request("GET", "/api/v3/account", data)

        return account

    def get_account_balance(self) -> dict:
        """
        Returns a dict balance of a account
        """

        account = self.get_account_details()["balances"]
        balances = dict()

        try:
            for a in account:
                balances[a["asset"]] = a["free"]
        except Exception as e:
            print(f"Problem with getting account balance. Accuring error: {e}")

        return balances

    def get_asset_balance(self, currency) -> float:
        """
        Returns a chosen asset balance of a account or None if there's no asset
        """
        """
        :param currency: type str of a chosen asset
        :return: type long of a asset balance or None
        """
        account = self.get_account_details()["balances"]
        try:
            for a in account:
                if str(currency) == str(a["asset"]):
                    return a["free"]
        except Exception as e:
            print(f"Problem with getting asset: {currency} of {e}.")

    def get_current_price(self, tick):
        """
        Returns latest price for a symbol or return all symbols tickers with None symbol param
        """
        symbol = {
            "symbol": str(tick),
        }
        try:
            ticker = self.make_request("GET", "/api/v3/ticker/price", symbol)
            if ticker is not None:
                return ticker['price']
        except Exception as e:
            print(f"Error while getting the current price of {tick} with {e}.")

    def get_order_status(self, symbol, orderId):
        """
        Returns a status of an order, based on OrderId
        """
        data = dict()
        data["symbol"] = str(symbol)
        data["orderId"] = str(orderId)
        data["timestamp"] = self.time.generate_current_timestamp()
        data["signature"] = self.generate_signature(data)

        try:
            status = self.make_request("GET", "/api/v3/order", data)
            if status is not None:
                return status
            else:
                print("Returned None order status.")
        except Exception as e:
            print(f"Error while getting the current price of {symbol} with exception of: {e}")

    def cancel_order(self, symbol, orderId):
        """
        Cancels an order and returns canceled order status
        """
        data = dict()
        data["symbol"] = str(symbol)
        data["orderId"] = str(orderId)
        data["timestamp"] = self.time.generate_current_timestamp()
        data["signature"] = self.generate_signature(data)

        try:
            status = self.make_request("DELETE", "/api/v3/order", data)
            if status is not None:
                return status
            else:
                print("Returned None order status.")
        except Exception as e:
            print(f"Error while canceling {symbol}, id: {orderId} with exception of: {e}")

    def cancel_all_orders(self, symbol):
        data = dict()
        data["symbol"] = str(symbol)
        data["timestamp"] = self.time.generate_current_timestamp()
        data["signature"] = self.generate_signature(data)

        try:
            status = self.make_request("DELETE", "/api/v3/openOrders", data)
            if status is not None:
                return status
            else:
                print("Returned None order status.")
        except Exception as e:
            print(f"Error while canceling all orders of {symbol}, with exception of: {e}")

    def is_enough_balance(self,
                          base_asset: str,
                          quote_asset: str,
                          order_amount: float,
                          order_market_type: str,
                          order_type: str) -> bool:
        """
        Checks if there's enough balance to trade with particular asset

        :param base_asset: type str of a chosen base asset
        :param quote_asset: type str of a chosen quote asset
        :param order_amount: amount of a asset that is trading with
        :param order_market_type: type of a market order
        :param order_type: BUY or SELL order
        :return: boolean, true if balance is enough to trade or false if not
        """
        symbol = str(base_asset).upper()+str(quote_asset).upper()
        base_balance = self.get_asset_balance(base_asset)
        quote_balance = self.get_asset_balance(quote_asset)

        try:
            if order_market_type == "quantity":
                if order_type == "BUY":
                    current_price = self.get_current_price(symbol)
                    order_price = current_price*order_amount

                    if quote_balance > order_price:
                        return True
                    else:
                        return False

                elif order_type == "SELL":
                    if order_amount <= base_balance:
                        return True
                    else:
                        return False

            elif order_market_type == "quoteOrderQty":
                if order_type == "BUY":
                    if order_amount < quote_balance:
                        return True
                    else:
                        return False
                elif order_type == "SELL":
                    if order_amount < quote_balance:
                        return True
                    else:
                        return False
            else:
                print("Wrong order type 'in is_enough_balance' method.")
        except Exception as e:
            print(f"Error while checking enough balance of a asset: {e}.")

    def buy_order(self, symbol, side="BUY", type="MARKET", timeInForce="GTC", price=0.0, amount=0.0, quantity_type="quantity"):
        """
        Make a BUY MARKET order
        """
        # Amount of asset you want to buy -> for instance 1 BTC
        data = dict()
        if quantity_type == "quantity":

            if type == "MARKET":
                data["symbol"] = str(symbol)
                data["side"] = str(side)
                data["type"] = str(type)
                data["quantity"] = float(amount)
                data["timestamp"] = self.time.generate_current_timestamp()
                data["signature"] = self.generate_signature(data)

            elif type == "LIMIT":
                data["symbol"] = str(symbol)
                data["side"] = str(side)
                data["type"] = str(type)
                data["timeInForce"] = str(timeInForce)
                data["quantity"] = float(amount)
                data["price"] = float(price)
                data["timestamp"] = self.time.generate_current_timestamp()
                data["signature"] = self.generate_signature(data)

            try:
                buy = self.make_request("POST", "/api/v3/order", data)
                return buy
            except Exception as e:
                print(
                    f"Couldn't handle {side} request of type {type}, with symbol {symbol} and quantity_type {quantity_type} with error {e}")

        # Amount of asset you would buy with particular amount of quote asset
        # -> for instance as much BTC as I get from 1USDT
        elif quantity_type == "quoteOrderQty":
            data["symbol"] = str(symbol)
            data["side"] = str(side)
            data["type"] = str(type)
            data["quoteOrderQty"] = float(amount)
            data["timestamp"] = self.time.generate_current_timestamp()
            data["signature"] = self.generate_signature(data)

            try:
                buy = self.make_request("POST", "/api/v3/order", data)
                return buy
            except Exception as e:
                print(
                    f"Couldn't handle {side} request of type {type}, with symbol {symbol} and quantity_type {quantity_type} with error {e}")
        else:
            print(f"Problem while chosing quantity type in {side} order of type {type}.")

    def sell_order(self, symbol, side="SELL", type="MARKET", timeInForce="GTC", price=0.0, amount=0.0, quantity_type="quantity"):
        """
        Make a SELL MARKET order
        """
        # Amount of asset you want to sell -> for instance 1 BTC
        data = dict()
        if quantity_type == "quantity":

            if type == "MARKET":
                data["symbol"] = str(symbol)
                data["side"] = str(side)
                data["type"] = str(type)
                data["quantity"] = float(amount)
                data["timestamp"] = self.time.generate_current_timestamp()
                data["signature"] = self.generate_signature(data)

            elif type == "LIMIT":
                data["symbol"] = str(symbol)
                data["side"] = str(side)
                data["type"] = str(type)
                data["timeInForce"] = str(timeInForce)
                data["quantity"] = float(amount)
                data["price"] = float(price)
                data["timestamp"] = self.time.generate_current_timestamp()
                data["signature"] = self.generate_signature(data)

            try:
                sell = self.make_request("POST", "/api/v3/order", data)
                return sell
            except Exception as e:
                print(
                    f"Couldn't handle {side} request of type {type}, with symbol {symbol} and quantity_type {quantity_type} with error {e}")

        # Amount of asset you would sell with particular amount of quote asset
        # -> for instance as much BTC as I get from 1USDT
        elif quantity_type == "quoteOrderQty":
            data["symbol"] = str(symbol)
            data["side"] = str(side)
            data["type"] = str(type)
            data["quoteOrderQty"] = float(amount)
            data["timestamp"] = self.time.generate_current_timestamp()
            data["signature"] = self.generate_signature(data)

            try:
                buy = self.make_request("POST", "/api/v3/order", data)
                return buy
            except Exception as e:
                print(
                    f"Couldn't handle {side} request of type {type}, with symbol {symbol} and quantity_type {quantity_type} with error {e}")
        else:
            print(f"Problem while chosing quantity type in {side} order of type {type}.")

    # WEBSOCKET API ----------------------------------------------------------------------------------------------------

    def start_ws(self, open, close, error, message):
        self.ws = websocket.WebSocketApp(self.wss_url, on_open=open, on_close=close, on_error=error,
                                         on_message=message)
        while True:
            try:
                self.ws.run_forever()
            except Exception as e:
                print(f"Binance resuming with info: {e}")
            time.sleep(2)

    def on_open_kline(self, ws):
        print("Websocket connection established")
        self.kline_subscribe(self.subscribe_symbol, self.subscribe_interval)

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WS connection closed with code: {close_status_code} and msg: {close_msg}")

    def on_error(self, ws, msg):
        print(f"Binance Websocket closed connection with message: {msg}. Establishing again...")

    def on_bookticker_message(self, ws, msg):
        data = json.loads(msg)

        if "u" in data:
            symbol = data['s']

            if symbol not in self.prices:
                self.prices[symbol] = {'bid': float(data['b']), 'ask': float(data['a'])}
            else:
                self.prices[symbol]['bid'] = float(data['b'])
                self.prices[symbol]['ask'] = float(data['a'])

            print(self.prices[symbol])

    def on_kline_message(self, ws, msg):
        data = json.loads(msg)

        if "e" in data:
            symbol = data['s']

            if symbol not in self.klines:
                self.klines[symbol] = {'start_time': pd.to_datetime(data['k']['t'], unit="ms"),
                                       'open': float(data['k']['o']),
                                       'high': float(data['k']['h']),
                                       'low': float(data['k']['l']),
                                       'close': float(data['k']['c']),
                                       'volume': float(data['k']['v']),
                                       'complete': data['k']['x'], }
            else:
                self.klines[symbol]['start_time'] = pd.to_datetime(data['k']['t'], unit="ms")
                self.klines[symbol]['open'] = float(data['k']['o'])
                self.klines[symbol]['high'] = float(data['k']['h'])
                self.klines[symbol]['low'] = float(data['k']['l'])
                self.klines[symbol]['close'] = float(data['k']['c'])
                self.klines[symbol]['volume'] = float(data['k']['v'])
                self.klines[symbol]['complete'] = data['k']['x']

        print(self.klines[symbol])

    def kline_subscribe(self, symbol, interval):
        """
        Subscribe to a Kline/Candlestick Streams
        """

        data = dict()
        data["method"] = "SUBSCRIBE"
        data["params"] = []
        data["params"].append(symbol.lower() + "@kline_" + interval)
        data["id"] = self.ws_id

        try:
            self.ws.send(json.dumps(data))
        except Exception as e:
            print(f"Websocket error while subscribing to: {symbol}, of {e}")

        self.ws_id += 1

    def subscribe_channel(self, symbol):
        """
        Subscribe to a channel to receive a data of a symbol book ticker
        """
        data = dict()
        data["method"] = "SUBSCRIBE"
        data["params"] = []
        data["params"].append(symbol.lower() + "@bookTicker")
        data["id"] = self.id

        self.ws.send(json.dumps(data))

        self.id += 1

    def get_symbol_kline_stream(self, symbol, interval):
        """
        Return Kline/Candlestick stream dict object with chosen symbol and interval
        """

        self.subscribe_symbol = symbol
        self.subscribe_interval = interval
        t = threading.Thread(
            target=self.start_ws(self.on_open_kline, self.on_close, self.on_error, self.on_kline_message))
        t.start()
