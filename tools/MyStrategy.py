from backtesting import Strategy

class MyStrategy(Strategy):

    def get_indicators(self):
        return self._indicators

