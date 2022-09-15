import pandas as pd
import numpy as np


class ExitRules:
    def __init__(self, last_price: float):
        self.last_price = last_price

    def stop_price(self, st_price) -> bool:
        """
        When the current price is lower than the Stop Price, trading bot will automatically sell out the base currency.
        """
        if self.last_price < st_price:
            return True
        else:
            return False

    def take_profit(self, tp_price) -> bool:
        """
        When the current price hit the Take Profit price, bot stops to work.
        """
        if self.last_price > tp_price:
            return True
        else:
            return False

