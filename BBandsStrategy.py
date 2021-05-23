#
# This version uses RSI(today) - RSI(yesterday) as RSI2
#
#

from backtesting import Strategy, Backtest
from backtesting.lib import resample_apply
import pandas as pd
import talib as ta
import logging


class MyStrategy(Strategy):
    def __init__(self, broker, data, params) -> None:
        super().__init__(broker, data, params)
        self.tradeinfo = []

    def get_indicators(self):
        return self._indicators

    def get_tradeinfo(self):
        return self.tradeinfo


logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s %(pathname)s %(lineno)d',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def BBANDS(data, n_lookback, n_std):
    """Bollinger bands indicator"""
    hlc3 = (data.High + data.Low + data.Close) / 3
    mean, std = hlc3.rolling(n_lookback).mean(), hlc3.rolling(n_lookback).std()
    upper = mean + n_std*std
    lower = mean - n_std*std
    return upper, lower


def get_strategy():
    return BBandsStrategy


def dailyReturn(values):
    s1 = pd.Series(values)
    s2 = pd.Series(values)
    return (s2.shift(-1) - s1) / s1  # Add log() ?


class BBandsStrategy(MyStrategy):
    strategy_param_rsi_lookback = 14  # Daily RSI lookback periods
    strategy_param_rsi_upper_limit = 80
    strategy_param_rsi_lower_limit = 20
    strategy_param_rsi_max_position_length = 8
    strategy_param_rsi_max_negative_position_length = 3

    strategy_param_bbands_period = 14

    def RSI2Positive(self):
        # RSI2 is positive if we have 3 consecutive days of +++
        # return self.rsi[-2] < self.rsi[-1]
        return self.rsi2[-1] < -0.001  # epsilon

    def RSI2Neutral(self):
        return not self.RSI2Positive() and not self.RSI2Negative()

    def RSI2Negative(self):
        # RSI2 is negative if we have 3 consecutive days of ---
        # return self.rsi[-2] > self.rsi[-1]
        return self.rsi2[-1] > 0.001  # epsilon

    def LongEntryRule(self):
        # Go Long if RSI is under strategy_param_rsi_lower_limit
        res = self.rsi[-1] < self.strategy_param_rsi_lower_limit
        # And RSI2 is positive
        res = res and self.RSI2Positive()
        if res:
            logging.info(
                f"LONGENTRYRULE: {self.rsi[-1]} < {self.strategy_param_rsi_lower_limit}")
        return res

    def ShortEntryRule(self):
        # Go Short if RSI is over strategy_param_rsi_upper_limit
        res = self.rsi[-1] > self.strategy_param_rsi_upper_limit
        # And RSI2 is negative
        res = res and self.RSI2Negative()
        if res:
            logging.info(
                f"LONGENTRYRULE: {self.rsi[-1]} > {self.strategy_param_rsi_upper_limit}")
        return res

    def ExitRule(self):
        # exit of position length is too long
        res = self.position_length > self.strategy_param_rsi_max_position_length
        # or we are losing money!
        res = res or (self.position_length > self.strategy_param_rsi_max_negative_position_length and
                      self.position.pl < 0)
        if res:
            logging.info(
                f"EXITRULE: {self.position_length} > {self.strategy_param_rsi_max_position_length}")
            logging.info(
                f"          {self.position_length} > {self.strategy_param_rsi_max_negative_position_length}")
        return res

    def init(self):
        self.rsi = self.I(ta.RSI, pd.Series(self.data.Close),self.strategy_param_rsi_lookback)
        self.rsi2 = self.I(dailyReturn, self.rsi)
        self.position_length = 0
        self.bbands = self.I(ta.BBANDS, pd.Series(self.data.Close), 14, 2, 2, 0)
        self.bbands_inner = self.I(ta.BBANDS, pd.Series(self.data.Close), 14, 1, 1, 0)
        
        self.redline = None
        self.blueline = None

        self.has_position = False

    def next(self):

        price = self.data.Close[-1]
        date = self.data.index[-1]

        high = self.bbands[0][-1]
        mid = self.bbands[1][-1]
        low = self.bbands[2][-1]

        if bool(self.has_position) != bool(self.position):
            if self.position:
                print(f"{date} 1+++ We now have a position!")
            else:
                print(f"{date} 1--- We dont have a position anymore!")
            self.has_position = bool(self.position)


        try:

            if price < low and not self.position:
                str = f"{date} Setting redline True since {price} < {low} and we have no position"
                self.tradeinfo.append(str)
                self.redline = True

            if price > high and self.position:
                str = f"{date} Setting blueline True since {price} > {high} and we have no position"
                self.tradeinfo.append(str)
                self.blueline = True

            if price > mid and not self.position and self.redline:
                str = f"{date} {price} > {mid} and we have no position and redline is set! BUY!!"
                self.tradeinfo.append(str)
                str = f"{date} Price = {price} Buying with SL={.92 * price} and TP={1.05 * price}"
                self.tradeinfo.append(str)
                self.buy(sl=.92 * price, tp=1.05 * price)

            if price > high and not self.position:
                str = f"{date} {price} > {high} and we have no position! BUY!!"
                self.tradeinfo.append(str)
                str = f"{date} Price = {price} Buying with SL={.92 * price} and TP={1.05 * price}"
                self.tradeinfo.append(str)
                self.buy(sl=.92 * price, tp=1.05 * price)

            if price < mid and self.position and self.blueline:
                str = f"{date} {price} < {mid} and we have no position! SELL!!"
                self.tradeinfo.append(str)
                str = f"{date} Price = {price} Selling with SL={1.08 * price} and TP={0.95 * price}"
                self.tradeinfo.append(str)
                self.sell(sl=1.08 * price, tp=0.95 * price)

                self.redline = False
                self.blueline = False

        except Exception as e:
            logging.error("--- EXCEPTION ---")
            logging.error(e)

        if bool(self.has_position) != bool(self.position):
            if self.position:
                logging.info(f"{date} 2+++ We now have taken a position!")
            else:
                print(f"{date} 2--- We dont have a position anymore!")
            self.has_position = bool(self.position)
