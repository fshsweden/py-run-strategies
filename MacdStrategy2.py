from backtesting import Strategy
from backtesting.lib import crossover
import talib as ta
import pandas as pd

def get_strategy():
    return MacdStrategy2

class MacdStrategy2(Strategy):
    # Define the two MA lags as *class variables*
    # for later optimization
    S = 12
    L = 26
    H = 9

    current_state = 0   # 0 = None, 1 = Break UP, -1 = Break Down

    def init(self):
        self.rsi = self.I(ta.RSI, pd.Series(self.data.Close), 14)
        self.rsi2 = self.I(ta.RSI, self.rsi, 14)  # RSI on RSI

        # macd = diff between EMA12 and EMA26
        # signal = ema9 on macd
        # hist = diff between macd and signal
        self.macd, self.macd_signal, self.macd_hist = self.I(ta.MACD,
                                                             pd.Series(self.data.Close),
                                                             MacdStrategy2.S,
                                                             MacdStrategy2.L,
                                                             MacdStrategy2.H)

    def next(self):

        stoploss_buy = 0.95*self.data.Close[-1]
        stoploss_sell = 1.05 * self.data.Close[-1]
        takeprofit_buy = 1.10*self.data.Close[-1]
        takeprofit_sell = 0.90 * self.data.Close[-1]

        # print("-------------------------- BAR ------------------------------------------------")
        if self.position:
            print(f"Current PnL of position is: {self.position}  {self.position.pl} ({self.position.pl_pct} pct)")

        #
        # First detect whether we are at a cross between MACD and SIGNAL
        #
        cross = 0

        # BULLISH SIGNAL
        if crossover(self.macd, self.macd_signal):
            cross = 1
        # BEARISH SIGNAL
        elif crossover(self.macd_signal, self.macd):
            cross = -1

        # Close long position if RSI > 80
        if self.position.is_long and self.rsi[-1] >= 80:
            # print("Closing position because of RSI!")
            self.position.close()
            self.current_state == 0
            return

        # Close long position if RSI > 80
        if self.position.is_short and self.rsi[-1] <= 20:
            # print("Closing position because of RSI!")
            self.position.close()
            self.current_state == 0
            return

        #
        #   First, if we already have a position + a cross, close it
        #
        if self.position and cross != 0:
            # print(f"Have position and CROSS {cross} - closing position")
            self.position.close()
            self.current_state == 0
            return

        #
        #   If we have a position + no cross. Do nothing. SL and TP takes care!
        #

        if self.position and cross == 0:
            # print(f"HAVE position and NO CROSS {cross} - return, no action")
            return

        #
        #   Last case, no position!
        #
        # print(f"No position. current cross state={self.current_state} todays cross={cross} MACD {self.macd[-2]}/{self.macd[-1]} SIGNAL {self.macd_signal[-2]}/{self.macd_signal[-1]}")

        if cross == 1:
            print(f"taking LONG position because of Signal {self.macd_signal[-2]} -> {self.macd_signal[-1]} MACD {self.macd[-2]} -> {self.macd[-1]})")
            self.buy(sl=stoploss_buy, tp=takeprofit_buy)
        elif cross == -1:
            print(f"taking SHORT position because of Signal {self.macd_signal[-2]} -> {self.macd_signal[-1]} MACD {self.macd[-2]} -> {self.macd[-1]})")
            self.sell(sl=stoploss_sell, tp=takeprofit_sell)
