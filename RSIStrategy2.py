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
    return RSIStrategy2


class RSIStrategy2(Strategy):
    strategy_param_rsi_lookback = 14  # Daily RSI lookback periods
    strategy_param_rsi_upper_limit = 85
    strategy_param_rsi_lower_limit = 15
    strategy_param_rsi_max_position_length = 14
    strategy_param_rsi_max_negative_position_length=3

    def RSI2Positive(self):
        # RSI2 is positive if we have 3 consecutive days of +++
        return self.rsi[-2] < self.rsi[-1]

    def RSI2Neutral(self):
        return not self.RSI2Positive() and not self.RSI2Negative()

    def RSI2Negative(self):
        # RSI2 is negative if we have 3 consecutive days of ---
        return self.rsi[-2] > self.rsi[-1]

    def LongEntryRule(self):
        # Go Long if RSI is under strategy_param_rsi_lower_limit
        res = self.rsi[-1] < self.strategy_param_rsi_lower_limit
        # And RSI2 is positive
        res = res and self.RSI2Positive()
        if res:
            logging.info(f"LONGENTRYRULE: {self.rsi[-1]} < {self.strategy_param_rsi_lower_limit}")
        return res

    def ShortEntryRule(self):
        # Go Short if RSI is over strategy_param_rsi_upper_limit
        res = self.rsi[-1] > self.strategy_param_rsi_upper_limit
        # And RSI2 is negative
        res = res and self.RSI2Negative()
        if res:
            logging.info(f"LONGENTRYRULE: {self.rsi[-1]} > {self.strategy_param_rsi_upper_limit}")
        return res

    def ExitRule(self):
        # exit of position length is too long
        res = self.position_length > self.strategy_param_rsi_max_position_length
        # or we are losing money!
        res = res or (self.position_length > self.strategy_param_rsi_max_negative_position_length and
                      self.position.pl < 0)
        if res:
            logging.info(f"EXITRULE: {self.position_length} > {self.strategy_param_rsi_max_position_length}")
            logging.info(f"          {self.position_length} > {self.strategy_param_rsi_max_negative_position_length}")
        return res

    def init(self):
        self.rsi = self.I(ta.RSI, pd.Series(self.data.Close), self.strategy_param_rsi_lookback)
        self.rsi2 = self.I(ta.RSI, self.rsi, self.strategy_param_rsi_lookback)  # RSI on RSI
        self.position_length = 0

    def next(self):

        #print("-in-----------------------")
        #print(self.orders)
        #print(self.trades)
        #print(self.closed_trades)
        #print("-out-----------------------")

        try:

            price = self.data.Close[-1]

            # If we don't already have a position, and
            # if all conditions are satisfied, enter long.
            if not self.position and self.LongEntryRule():
                # Buy at market price on next open, but do
                # set 8% fixed stop loss.
                self.buy(sl=.92 * price)
            elif not self.position and self.ShortEntryRule():
                # Sell at market price on next open, but do
                # set 8% fixed stop loss.
                self.sell(sl=1.08 * price)

            #
            # Increment position times
            #

            if not self.position:
                self.position_length = 0
            else:
                self.position_length = self.position_length + 1

                # Keep position max 14 periods
                # Keep position while P&L is increasing
                if self.position and self.ExitRule():
                    logging.info(f"PNL is now {self.position.pl} - closing")
                    self.position.close()
                    self.position_length = 0

        except Exception as e:
            logging.error("--- EXCEPTION ---")
            logging.error(e)

