from backtesting import Strategy
from backtesting.lib import crossover
import talib as ta
import pandas as pd

def get_strategy():
    return MacdStrategy

class MacdStrategy(Strategy):
    # Define the two MA lags as *class variables*
    # for later optimization
    S = 12
    L = 26
    H = 9

    current_state = 0   # 0 = None, 1 = Break UP, -1 = Break Down

    def __reduce__(self):
        pass

    def init(self):
        self.rsi = self.I(ta.RSI, pd.Series(self.data.Close), 14)
        self.macd, self.macd_signal, self.macd_hist = self.I(ta.MACD,
                                                             pd.Series(self.data.Close),
                                                             MacdStrategy.S,
                                                             MacdStrategy.L,
                                                             MacdStrategy.H)

    def next(self):

        stoploss_buy = 0.98*self.data.Close
        stoploss_sell = 0.02 * self.data.Close
        takeprofit_buy = 1.05*self.data.Close
        takeprofit_sell = 0.95 * self.data.Close

        #
        # First detect whether we are at a cross (UP or DOWN)
        #
        cross = 0
        # BULLISH SIGNAL
        if crossover(self.macd, self.macd_signal):
            cross = 1
        # BEARISH SIGNAL
        elif crossover(self.macd_signal, self.macd):
            cross = -1

        #print(f"current state={self.current_state} bar-cross={cross} MACD={self.macd[-1]} SIGNAL={self.macd_signal[-1]}")

        #
        # Weäre not looking and nothing happened, exit!
        #
        if self.current_state == 0 and cross == 0:
            return

        #
        # Are we currently LOOKING UP or DOWN?
        #
        if self.current_state == 0:
            # NO. Change to UP or DOWN.
            self.current_state = cross
        else:
            # YES. A cross will terminate that LOOKING state
            if cross != 0:
                self.current_state = 0



        if self.current_state != -1 and self.macd[-1] >= 0:
            #print(f"All is OK to take LONG position. Must check RSI though: {self.rsi[-1]}")
            self.position.close()
            #if self.rsi[-1] <= 30:
            #print(f"taking LONG position because of Signal {self.macd_signal[-2]} -> {self.macd_signal[-1]} MACD {self.macd[-2]} -> {self.macd[-1]} and  RSI({self.rsi[-1]})")
            self.buy(tp=takeprofit_buy)
            self.current_state = 0  # Not looking!
        else:
            if self.current_state != 1 and self.macd[-1] <= 0:
                #print(f"All is OK to take SHORT position. Must check RSI though: {self.rsi[-1]}")
                self.position.close()
                #if self.rsi[-1] >= 70:
                #print(
                #    f"taking SHORT position because of Signal {self.macd_signal[-2]} -> {self.macd_signal[-1]} MACD {self.macd[-2]} -> {self.macd[-1]} and  RSI({self.rsi[-1]})")
                self.sell(tp=takeprofit_sell)
                self.current_state = 0  # Not looking!

        #print("--- done with this bar ---")