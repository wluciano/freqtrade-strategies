# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

import datetime
from typing import Optional
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.persistence import Trade

class hlhb(IStrategy):
    """
    The HLHB ("Huck loves her bucks!") System simply aims to catch short-term forex trends.
    More information in https://www.babypips.com/trading/forex-hlhb-system-explained
    """
    can_short = True

    INTERFACE_VERSION: int = 3

    #position_stacking = "True"

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 0.32,
        "30": 0.16,
        "60": 0.08,
        "480": -1 #
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -1

    # Trailing stoploss
    #trailing_stop = True
    #trailing_stop_positive = 0.08
    #trailing_stop_positive_offset = 0.16
    #trailing_only_offset_is_reached = True

    # Optimal timeframe for the strategy.
    timeframe = '3m'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the "ask_strategy" section in the config.
    use_exit_signal = True
    exit_profit_only = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': True
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }

    plot_config = {
        # Main plot indicators (Moving averages, ...)
        'main_plot': {
            'ema5': {},
            'ema10': {},
        },
        'subplots': {
            # Subplots - each dict defines one additional plot
            "RSI": {
                'rsi': {'color': 'red'},
            },
            "ADX": {
                'adx': {},
            }
        }
    }

    use_custom_stoploss = True

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:

        baseProfit = 0.04

        if pair == "ETH/USDT":
            baseProfit = 0.08

        if current_profit < baseProfit:
            return -1 # return a value bigger than the inital stoploss to keep using the inital stoploss

        # After reaching the desired offset, allow the stoploss to trail by half the profit
        desired_stoploss = current_profit / 2 

        # Use a minimum of 2% and a maximum of 8%
        return max(min(desired_stoploss, baseProfit * 2), baseProfit / 2)

    def informative_pairs(self):
        return []

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], side: str,
                 **kwargs) -> float:
        """
        Customize leverage for each new trade. This method is only called in futures mode.

        :param pair: Pair that's currently analyzed
        :param current_time: datetime object, containing the current datetime
        :param current_rate: Rate, calculated based on pricing settings in exit_pricing.
        :param proposed_leverage: A leverage proposed by the bot.
        :param max_leverage: Max leverage allowed on this pair
        :param entry_tag: Optional entry_tag (buy_tag) if provided with the buy signal.
        :param side: 'long' or 'short' - indicating the direction of the proposed trade
        :return: A leverage amount, which is between 1.0 and max_leverage.
        """
        
        return 5 if pair == "ETH/USDT" else 2

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['hl2'] = (dataframe["close"] + dataframe["open"]) / 2

        # Momentum Indicators
        # ------------------------------------

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=10, price='hl2')

        # # EMA - Exponential Moving Average
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema10'] = ta.EMA(dataframe, timeperiod=10)

        # ADX
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=28)

        return dataframe

    def go_long_entry(self, dataframe: DataFrame, metadata: dict) -> bool:
        return (
                (qtpylib.crossed_above(dataframe['rsi'], 50)) &
                (qtpylib.crossed_above(dataframe['ema5'], dataframe['ema10'])) &
                (dataframe['adx'] > 25) &
                (dataframe['volume'] > 0) # Make sure Volume is not 0
            )

    def go_short_entry(self, dataframe: DataFrame, metadata: dict) -> bool:
        return (
                (qtpylib.crossed_below(dataframe['rsi'], 50)) &
                (qtpylib.crossed_below(dataframe['ema5'], dataframe['ema10'])) &
                (dataframe['adx'] > 25) &
                (dataframe['volume'] > 0)  # Make sure Volume is not 0
            )

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[self.go_long_entry(dataframe, metadata), 'enter_long'] = 1
        dataframe.loc[self.go_short_entry(dataframe, metadata), 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[self.go_short_entry(dataframe, metadata), 'exit_long'] = 1
        dataframe.loc[self.go_long_entry(dataframe, metadata), 'exit_short'] = 1

        return dataframe

