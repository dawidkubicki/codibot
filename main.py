import keys.keys as keys
from time_operators.time_operator import TimeOperator
from bots.ta_bots.ema_crossover import EMACrossoverBOT
# from bots.bot import Bot
from bots.grid.spot_grid import StaticGridBot
from config.title import TITLE
from config.intervals import INTERVALS

units = 0.001
position = 0
tc = -0.00085

time = TimeOperator()

available_strategies = ["triple_sma", "triple_ema", "macd", "rsi", "ichimoku_cloud"]
symbols = ["BTCUSDT", "ADAUSDT", "SANDUSDT", "MBOXUSDT", "ETHUSDT", "DOTUSDT", "SOLUSDT"]

strategy = "triple_sma"
period_cagr = "month"
fee = 0.1

if __name__ == "__main__":
    keepWorking = True
    while keepWorking:
        print(TITLE)
        bot = EMACrossoverBOT(
            key=keys.testnet_api_key,
            secret=keys.testnet_secret_key,
            use_testnet=True,
            base_symbol="btc",
            quote_symbol="usdt",
            bar_length=INTERVALS["ONE_MINUTE"],
            strategy_type="triple_ema",
            units=units,
            atr_stop_loss=False,
            trailing_stop_loss=True,
            fixed_stop_loss=False,
            atr_stop_loss_own_smoothing=False,
            stop_loss=1.05,
            take_profit=1.000000001
        )
        bot.start_trading(historical_days=14)


#
# bot = StaticGridBot(key=keys.testnet_api_key,
#                     secret=keys.testnet_secret_key,
#                     use_testnet=True,
#                     base_symbol="btc",
#                     quote_symbol="usdt",
#                     units=0.001,
#                     fee=fee,
#                     upper_price=30000.00,
#                     lower_price=24000.00,
#                     num_grids=8,
#                     stop_loss_active=True,
#                     stop_loss=25000.00,
#                     take_profit_active=True,
#                     take_profit=30000.0,
#                     sale_base_asset=False,
#                     )
#
# bot.start_grid_bot_trading()

# ichimoku_tester = IchimokuCloudRSI(key=keys.testnet_api_key,
#                                    secret=keys.testnet_secret_key,
#                                    use_testnet=False,
#                                    interval=SIX_HOUR,
#                                    start=time.generate_reverse_days(60),
#                                    symbols=symbols,
#                                    strategy=strategy,
#                                    tc=tc,
#                                    period_cagr=period_cagr)
#
# # ichimoku_tester.all_combinantion(conversion_window_range=range(8, 12),
# #                                  base_window_range=range(25, 28),
# #                                  span_window_range=range(52, 54),
# #                                  leading_shift_range=range(25, 28),
# #                                  lagging_shift_range=range(25, 28))
#
# ichimoku_tester.ichimoku_cloud_rsi(atr_stop_loss=False,
#                                    trailing_stop_loss=False,
#                                    fixed_stop_loss=True,
#                                    stop_loss=0.995)

# bot = SMACrossoverBOT(key=keys.testnet_api_key,
#                       secret=keys.testnet_secret_key,
#                       use_testnet=True,
#                       base_symbol="btc",
#                       quote_symbol="usdt",
#                       bar_length=ONE_MINUTE,
#                       strategy_type="triple_sma",
#                       units=units,
#                       atr_stop_loss=True,
#                       trailing_stop_loss=False,
#                       fixed_stop_loss=False,
#                       atr_stop_loss_own_smoothing=False,
#                       stop_loss=1.05,
#                       take_profit=1.01)
# bot.start_trading(7)

# ichimoku_tester = IchimokuCloud(key=keys.testnet_api_key,
#                                 secret=keys.testnet_secret_key,
#                                 use_testnet=True,
#                                 interval=SIX_HOUR,
#                                 start=time.generate_reverse_days(60),
#                                 symbols=symbols,
#                                 strategy=strategy,
#                                 tc=tc,
#                                 period_cagr=period_cagr)
# ichimoku_tester.ichimoku_cloud(atr_stop_loss=False,
#                                trailing_stop_loss=True,
#                                fixed_stop_loss=False,
#                                take_profit_percentage=1.05,
#                                fixed_take_profit=True,
#                                trailing_take_profit=False)
# ichimoku_tester.run_backtest()
# ichimoku_tester.measure_performance(print_performance=True)

#
# # ema_tester.all_combinantion(EMA_S_range=range(20, 40, 1),
# #                             EMA_M_range=range(50, 70, 1),
# #                             EMA_L_range=range(100, 120, 1))
#
# ichimoku_tester.all_combinantion(conversion_window_range=range(8, 12),
#                                  base_window_range=range(25, 28),
#                                  span_window_range=range(52, 54),
#                                  leading_shift_range=range(25, 28),
#                                  lagging_shift_range=range(25, 28))
# ichimoku_tester.ichimoku_cloud(atr_stop_loss=False, trailing_stop_loss=True, exit_rules=0.9992)
# ichimoku_tester.run_backtest()
# ichimoku_tester.measure_performance(print_performance=True)

# tester = RSI(key=keys.testnet_api_key,
#              secret=keys.testnet_secret_key,
#              use_testnet=False,
#              interval=ONE_MINUTE,
#              start=time.generate_reverse_days(50),
#              symbols=symbols,
#              strategy=strategy,
#              tc=tc,
#              period_cagr=period_cagr)
#
# tester.rsi(window=14,
#            frame=4,
#            K=4,
#            ema_s=12,
#            ema_m=14,
#            rsi_small=50,
#            rsi_big=50,
#            lags=4,
#            divergence_regular=False)
# tester.run_backtest()
# tester.measure_performance(print_performance=True)

# tester = STO_RSI_MACD(key=keys.testnet_api_key,
#                       secret=keys.testnet_secret_key,
#                       use_testnet=False,
#                       interval=THIRTY_MINUTE,
#                       start=time.generate_reverse_days(90),
#                       symbols=symbols,
#                       strategy=strategy,
#                       tc=tc,
#                       period_cagr=period_cagr)
#
# tester.all_combinantion(k_period_range=range(10, 20),
#                         smoothing_k_range=range(2, 4),
#                         d_period_range=range(2, 4),
#                         ema_fast_range=range(8, 16),
#                         ema_slow_range=range(18, 32),
#                         ema_sign_range=range(6, 12),
#                         rsi_window_range=range(12, 20),
#                         lags_range=range(2, 6),
#                         shift_position_range=range(0, 3))

# tester.sto_rsi_macd(k_period=14,
#                     smoothing_k=3,
#                     d_period=3,
#                     ema_fast=12,
#                     ema_slow=26,
#                     ema_sign=9,
#                     rsi_window=14,
#                     lags=4,
#                     shift_position=1)
#
# tester.run_backtest()
# tester.measure_performance(print_performance=True)
# rsi_tester.rsi(window=14, frame=5, K=2, ema_s=50, ema_m=150, rsi_buy=50, rsi_sell=50)
# rsi_tester.run_backtest()
# rsi_tester.measure_performance(print_performance=True)

# macd_tester = MACD(key=keys.testnet_api_key,
#                    secret=keys.testnet_secret_key,
#                    use_testnet=False,
#                    interval=ONE_DAY,
#                    start=time.generate_reverse_days(365),
#                    symbols=symbols,
#                    strategy=strategy,
#                    tc=tc,
#                    period_cagr=period_cagr)

# macd_tester.macd(12, 26, 9, technical=True, shifting=False)
# macd_tester.run_backtest()
# macd_tester.measure_performance(print_performance=True)

# macd_tester.all_combinantion(EMA_S_range=range(5, 20, 1),
#                              EMA_M_range=range(20, 30, 1),
#                              EMA_signal_range=range(2, 15, 1))

# ema_tester = EMA(key=keys.testnet_api_key,
#                  secret=keys.testnet_secret_key,
#                  use_testnet=False,
#                  interval=ONE_DAY,
#                  start=time.generate_reverse_days(365),
#                  symbols=symbols,
#                  strategy=strategy,
#                  tc=tc,
#                  period_cagr=period_cagr)
# #
# # # ema_tester.all_combinantion(EMA_S_range=range(20, 40, 1),
# # #                             EMA_M_range=range(50, 70, 1),
# # #                             EMA_L_range=range(100, 120, 1))
# #
# ema_tester.triple_ema(20, 50, 100, atr_stop_loss=False, trailing_stop_loss=True, exit_rules=0.9995)
# ema_tester.run_backtest()
# ema_tester.measure_performance(print_performance=True)

# exit_rules = None
# trailing_stop_loss = False
#
# sma_tester = SMA(key=keys.testnet_api_key,
#                  secret=keys.testnet_secret_key,
#                  use_testnet=False,
#                  interval=ONE_HOUR,
#                  start=time.generate_reverse_days(120),
#                  symbols=symbols,
#                  strategy=strategy,
#                  tc=tc,
#                  period_cagr=period_cagr)
#
# # sma_tester.all_combinantion(SMA_S_range=range(20,23,1), SMA_M_range=range(50,53,1), SMA_L_range=range(100,103,1))
#
# sma_tester.triple_sma(20, 50, 100)
# sma_tester.run_backtest()
# sma_tester.measure_performance(print_performance=True)
#


#

# sma_tester.triple_sma(15, 35, 120, technical=True, shifting=False)
# sma_tester.run_backtest()
# sma_tester.print_performance()

# sma_tester.triple_sma(10, 20, 50, technical=True, shifting=False)
# sma_tester.run_backtest()
# sma_tester.print_performance()

# tester = TABacktester(key=keys.testnet_api_key,
#                       secret=keys.testnet_secret_key,
#                       use_testnet=False,
#                       symbol=symbol,
#                       strategy_type="triple_ema",
#                       interval=THIRTY_MINUTE,
#                       start=time.generate_reverse_days(364),
#                       # triple ma
#                       ma_s_range=range(10, 21),
#                       ma_m_range=range(20, 31),
#                       ma_l_range=range(30, 51),
#                       # macd rsi
#                       ma_signal_range=range(40, 51),
#                       window_range=range(130, 151),
#                       ma_range=range(40, 51),
#                       rsi_buy_range=range(50, 61),
#                       rsi_sell_range=range(80, 91)
#                       )

# tester.implement_strategy(window=200, ma=19, rsi_sell=80, rsi_buy=30, ma_s=10, ma_m=20, ma_l=46, ma_signal=60)
# tester.test_strategy()
# tester.print_performance()


# if __name__ == "__main__":
#     works = True
#     while works:
#         print("======== Welcome to Codibot ======== \n")
#         decision = input("Would you like to trade / backtest? : ")
#
#         if decision == "trade":
#             strategy = input(" 1/5 |=>       | \nChoose the strategy \ntriple_sma | triple_ema | macd | rsi : ")
#             if strategy not in available_strategies:
#                 print("No such strategy!")
#                 break
#             symbol = input(" 2/5 |===>     | \nChoose the symbol : ")
#             interval = input(" 3/5 |=====>   |\nChoose the interval : ")
#             if interval not in available_intervals:
#                 print("No such interval!")
#                 break
#             amount_units = float(input("4/5 |=======> |\nChoose amount of units to trade : "))
#             sl = input("5/5 |=========>| \nSet the stop loss : ")
#             historical_days = float(input("\nHow many days from the past download: "))
#
#             if strategy == "triple_sma":
#                 ma1 = int(input("SMA1 = "))
#                 ma2 = int(input("SMA2 = "))
#                 ma3 = int(input("SMA3 = "))
#
#                 bot = Bot(key=keys.testnet_api_key,
#                           secret=keys.testnet_secret_key,
#                           use_testnet=True,
#                           symbol=symbol,
#                           bar_length=interval,
#                           strategy_type=strategy,
#                           units=amount_units,
#                           exit_rules=sl,
#                           position=position,
#                           ma_s=ma1,
#                           ma_m=ma2,
#                           ma_l=ma3,
#                           ma_signal=ma_signal,
#                           window=window,
#                           ma=ma,
#                           rsi_threshold_buy=rsi_threshold_buy,
#                           rsi_threshold_sell=rsi_threshold_sell)
#
#             elif strategy == "triple_ema":
#                 ma1 = int(input("EMA1 = "))
#                 ma2 = int(input("EMA2 = "))
#                 ma3 = int(input("EMA3 = "))
#
#                 bot = Bot(key=keys.testnet_api_key,
#                           secret=keys.testnet_secret_key,
#                           use_testnet=True,
#                           symbol=symbol,
#                           bar_length=interval,
#                           strategy_type=strategy,
#                           units=amount_units,
#                           exit_rules=sl,
#                           position=position,
#                           ma_s=ma1,
#                           ma_m=ma2,
#                           ma_l=ma3,
#                           ma_signal=ma_signal,
#                           window=window,
#                           ma=ma,
#                           rsi_threshold_buy=rsi_threshold_buy,
#                           rsi_threshold_sell=rsi_threshold_sell)
#                 bot.start_trading(historical_days)
#
#         elif decision == "backtest":
#             print("no")
#
#         else:
#             print("Wrong decision!")

#  1.002605
# Multiple (Buy-and-Hold):     0.757702
# tester = TABacktester(key=keys.testnet_api_key,
#                       secret=keys.testnet_secret_key,
#                       use_testnet=False,
#                       symbol=symbol,
#                       strategy_type="triple_ema",
#                       interval=THIRTY_MINUTE,
#                       start=time.generate_reverse_days(364),
#                       # triple ma
#                       ma_s_range=range(10, 21),
#                       ma_m_range=range(20, 31),
#                       ma_l_range=range(30, 51),
#                       # macd rsi
#                       ma_signal_range=range(40, 51),
#                       window_range=range(130, 151),
#                       ma_range=range(40, 51),
#                       rsi_buy_range=range(50, 61),
#                       rsi_sell_range=range(80, 91)
#                       )

# tester.implement_strategy(window=200, ma=19, rsi_sell=80, rsi_buy=30, ma_s=10, ma_m=20, ma_l=46, ma_signal=60)
# tester.test_strategy()
# tester.print_performance()
# bot = Bot(key=keys.testnet_api_key,
#           secret=keys.testnet_secret_key,
#           use_testnet=True,
#           symbol=symbol,
#           bar_length=ONE_MINUTE,
#           strategy_type=strategy_type,
#           units=units,
#           exit_rules=exit_rules,
#           position=position,
#           ma_s=ma_s,
#           ma_m=ma_m,
#           ma_signal=ma_signal,
#           window=window,
#           ma=ma,
#           rsi_threshold_buy=rsi_threshold_buy,
#           rsi_threshold_sell=rsi_threshold_sell)
# bot.start_trading(14)
