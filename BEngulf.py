#
# This version uses RSI(today) - RSI(yesterday) as RSI2
#
#

from backtesting import Strategy, Backtest
from backtesting.lib import resample_apply
import pandas as pd
import talib as ta
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s %(pathname)s %(lineno)d',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


def get_strategy():
    return BEngulf

def dailyReturn(values):
    s1 = pd.Series(values)
    s2 = pd.Series(values)
    return (s2.shift(-1) - s1) / s1

class BEngulf(Strategy):

    strategy_param_rsi_lookback = 14  # Daily RSI lookback periods
    strategy_param_rsi_upper_limit = 80
    strategy_param_rsi_lower_limit = 20
    strategy_param_rsi_max_position_length = 8
    strategy_param_rsi_max_negative_position_length=3

    def RSIOverBought(self):
        return self.rsi[-1] > self.strategy_param_rsi_upper_limit

    def RSIOverSold(self):
        return self.rsi[-1] < self.strategy_param_rsi_lower_limit

    def RSI2Positive(self):
        # RSI2 is positive if we have 3 consecutive days of +++
        # return self.rsi[-2] < self.rsi[-1]
        return self.rsi2[-1] < -0.001 # epsilon

    def RSI2Neutral(self):
        return not self.RSI2Positive() and not self.RSI2Negative()

    def RSI2Negative(self):
        # RSI2 is negative if we have 3 consecutive days of ---
        # return self.rsi[-2] > self.rsi[-1]
        return self.rsi2[-1] > 0.001  # epsilon


    def whiteCandle(self, index):
        return self.data.Close[index] >= self.data.Open[index]

    def blackCandle(self, index):
        return self.data.Close[index] < self.data.Open[index]

    def LongEntryRule(self):
        # if we have three black candles in a row
        if self.blackCandle(-2) and self.blackCandle(-3) and self.blackCandle(-4):
            if self.data.Open[-1] < self.data.Close[-2] and self.data.Close[-1] > self.data.Open[-2]:

                if (self.RSIOverSold()):
                    logging.info(f"LONGENTRYRULE TRIGGERED")
                    return True
        return False

    def ShortEntryRule(self):
        # if we have three black candles in a row
        if self.whiteCandle(-2) and self.whiteCandle(-3) and self.whiteCandle(-4):
            if self.data.Close[-1] < self.data.Open[-2] and self.data.Open[-1] > self.data.Close[-2]:
                if (self.RSIOverBought()):
                    logging.info(f"SHORTENTRYRULE TRIGGERED")
                    return True
        return False


    def ExitRule(self):
        # exit of position length is too long
        res = self.position_length >= 5
        # or we are losing money!
        res = res or (self.position_length >= 2 and self.position.pl < 0)
        if res:
            logging.info(f"EXITRULE TRIGGERED")
        return res

    def init(self):
        self.rsi = self.I(ta.RSI, pd.Series(self.data.Close), self.strategy_param_rsi_lookback)
        self.rsi2 = self.I(dailyReturn, self.rsi)
        self.position_length = 0

    def next(self):

        if self.position:
            logging.info(f"TICK: HAS POSIION'")

        try:

            price = self.data.Close[-1]

            # IS NO POS, TEST ENTRYRULE 
            if not self.position and self.LongEntryRule():
                # Buy at market price on next open, but do
                # set 8% fixed stop loss.
                self.buy(sl=.92 * price, tp=1.15 * price)
            elif not self.position and self.ShortEntryRule():
                # Sell at market price on next open, but do
                # set 8% fixed stop loss.
                self.sell(sl=1.08 * price, tp=0.85 * price)

            #
            # HANDLE POS LENGTH
            #
            if not self.position:
                self.position_length = 0
            else:
                self.position_length = self.position_length + 1

                # Test EXITRULE!
                if self.position and self.ExitRule():
                    logging.info(f"PNL is now {self.position.pl} - closing")
                    self.position.close()
                    self.position_length = 0

        except Exception as e:
            logging.error("--- EXCEPTION ---")
            logging.error(e)

