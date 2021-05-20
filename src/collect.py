import argparse
import asyncio
from loguru import logger
import time
import datetime


def set_logger(data_dir: str):
    """
    set logging behavior, and handles compression, rotation automatically
    :param data_dir:
    :param ticker:
    :param ex:
    :return:
    """
    logger.remove()
    data_prefix = f"{data_dir}{exchange_name}/{symbol}/{data_type}"
    logger.add(
        f"{data_prefix}/parsed/{{time}}.csv",
        format="{message}",
        rotation="256 MB",
        compression="gz",
        filter=lambda record: "task" in record["extra"] and record["extra"]["task"] == task_name
    )
    logger.add(
        f"{data_prefix}/raw/{{time}}.txt",
        format="{message}",
        rotation="256 MB",
        compression="gz",
        filter=lambda record: "task" in record["extra"] and record["extra"]["task"] == f"{task_name}_raw"
    )


async def binance_tick_trade_data():
    """
    collect binance_tick_trade_data
    :return:
    """
    from binance import AsyncClient, BinanceSocketManager

    raw_data_logger = logger.bind(task=f"{task_name}_raw")
    data_logger = logger.bind(task=task_name)

    def process_binance_trade_socket_msg(msg):
        """
        parser and logger helper specific to binance tick trade data
        :param msg:
        :return:
        """
        raw_data_logger.info(msg)
        # e: trade, E: event time, s: symbol, t: Trade ID, p: Price, q: Quantity, T: trade time, m: mm or not

        # note: difference between event time and trade time
        # https://stackoverflow.com/questions/50688471/binance-event-time-vs-trade-time
        try:
            parsed_msg = f"{msg['E']},{msg['s']},{msg['t']},{msg['p']},{msg['q']}," \
                         f"{msg['T']},{msg['m']}"

            data_logger.info(parsed_msg)
        except Exception as e:
            logger.error(e)
            # send alerts to slack / telegram + PagerDuty

    client = await AsyncClient.create()
    bsm = BinanceSocketManager(client)

    async with bsm.trade_socket(symbol) as socket:
        while True:
            res = await socket.recv()
            process_binance_trade_socket_msg(res)


async def binance_order_book_snapshot():
    """
    get binance snapshot of order book
    :return:
    """
    from binance import AsyncClient, DepthCacheManager

    client = await AsyncClient.create()
    dcm = DepthCacheManager(client, symbol)
    raw_data_logger = logger.bind(task=f"{task_name}_raw")
    data_logger = logger.bind(task=task_name)
    depth = 5

    async with dcm as dcm_socket:
        while True:
            depth_cache = await dcm_socket.recv()
            update_time = depth_cache.update_time
            depth_symbol = depth_cache.symbol
            bids = depth_cache.get_bids()[:depth]
            asks = depth_cache.get_asks()[:depth]
            msg = {
                'update_time': update_time,
                'symbol': depth_symbol,
                'bids': bids,
                'asks': asks,
                'depth': depth
            }
            raw_data_logger.info(msg)
            try:
                parsed_data = ""
                for i in range(depth):
                    bid_msg = f"{update_time}," \
                              f"{symbol}," \
                              f"B," \
                              f"{bids[i][0]}," \
                              f"{bids[i][1]}," \
                              f"{i + 1}"
                    ask_msg = f"{update_time}," \
                              f"{symbol}," \
                              f"A," \
                              f"{asks[i][0]}," \
                              f"{asks[i][1]}," \
                              f"{i + 1}"
                    parsed_data += f"\n{bid_msg}\n{ask_msg}"

                data_logger.info(parsed_data.strip())
            except Exception as e:
                logger.error(e)
                # send alerts to slack / telegram + PagerDuty


async def collect_binance():
    """
    citation: https://python-binance.readthedocs.io/en/latest/websockets.html#binancesocketmanager-websocket-usage
    process all tick data using async client for a particular symbol. detailed can be found in the link above
    :return:
    """
    if data_type == "trade":
        await binance_tick_trade_data()
    elif data_type == "book":
        await binance_order_book_snapshot()
    else:
        raise ValueError(f"invalid data_type: {data_type}")


def unix_time_millis(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return round((dt - epoch).total_seconds() * 1000.0)


def parse_z_str_to_dt(s):
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')


def coinbase_tick_trade_data():
    """
    get coinbase tick trade data (orders that have been matched and taken off the order book)
    future enhacement note: we can add heartbeat channel to track the last trade id
    and fetch trade that we potentially miss from the REST API in concurrent with this process.

    link: https://docs.pro.coinbase.com/#the-matches-channel

    :return:
    """
    from copra.websocket import Channel, Client
    raw_data_logger = logger.bind(task=f"{task_name}_raw")
    data_logger = logger.bind(task=task_name)

    class CoinbaseClient(Client):
        def on_message(self, msg):
            if msg['type'] == 'match':
                raw_data_logger.info(msg)
                try:
                    trade_time = parse_z_str_to_dt(msg['time'])
                    trade_time_in_millis = unix_time_millis(trade_time)
                    data_logger.info(f"{round(time.time() * 1000)},"  # socket time
                                     f"{msg['product_id']},"  # e.g. BTC-USD
                                     f"{msg['trade_id']},"
                                     f"{msg['price']},"
                                     f"{msg['size']},"  # quantity
                                     f"{trade_time_in_millis},"
                                     f"{True if msg['side'] == 'buy' else False}")  # is the Buyer the market maker?
                except Exception as e:
                    logger.error(e)
                    # send alerts to slack / telegram + PagerDuty

    channel = Channel('matches', symbol)
    ws = CoinbaseClient(loop, channel)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(ws.close())


def coinbase_order_book_snapshot():
    from copra.websocket import Channel, Client
    raw_data_logger = logger.bind(task=f"{task_name}_raw")
    data_logger = logger.bind(task=task_name)

    class OrderBookWebSocketClient(Client):

        def __init__(self, loop, channel):
            super().__init__(loop, channel)
            self.depth_cache = {
                'A': [],
                'B': []
            }
            self.depth = 5  # subject to change
            self.frequency = 1000  # in milliseconds
            self.elastic_ratio = 3  # to avoid vanishing boundary problem

        def on_message(self, msg):
            if "type" in msg and msg['type'] == "l2update":
                raw_data_logger.info(msg)
                try:
                    # parse L2 updates
                    change = msg['changes']
                    if change[0][0] == 'buy':
                        # dedup
                        self.depth_cache['B'] = [i for i in self.depth_cache['B'] if i[0] != float(change[0][1])]
                        self.depth_cache['B'].append(
                            (
                                float(change[0][1]),  # price
                                float(change[0][2])   # quantity
                            )
                        )
                    elif change[0][0] == 'sell':
                        # dedup
                        self.depth_cache['A'] = [i for i in self.depth_cache['A'] if i[0] != float(change[0][1])]
                        self.depth_cache['A'].append(
                            (
                                float(change[0][1]),  # price
                                float(change[0][2])   # quantity
                            )
                        )
                    else:
                        logger.error(f"invalid record: {msg}")

                    self.depth_cache['A'] = [r for r in self.depth_cache['A'] if r[1] != 0]
                    self.depth_cache['A'].sort(key=lambda r: r[0], reverse=False)
                    self.depth_cache['A'] = self.depth_cache['A'][:self.depth*self.elastic_ratio]

                    self.depth_cache['B'] = [r for r in self.depth_cache['B'] if r[1] != 0]
                    self.depth_cache['B'].sort(key=lambda r: r[0], reverse=True)
                    self.depth_cache['B'] = self.depth_cache['B'][:self.depth*self.elastic_ratio]

                    msg_dt = parse_z_str_to_dt(msg['time'])
                    msg_mili = unix_time_millis(msg_dt)

                    if len(self.depth_cache['A']) >= 5 and len(self.depth_cache['B']) >= 5 \
                            and msg_mili % 1000 == 0:
                        parsed_data = ""
                        for i in range(self.depth):
                            bid_msg = f"{msg_mili}," \
                                      f"{msg['product_id']}," \
                                      f"B," \
                                      f"{self.depth_cache['B'][i][0]}," \
                                      f"{self.depth_cache['B'][i][1]}," \
                                      f"{i + 1}"
                            ask_msg = f"{msg_mili}," \
                                      f"{msg['product_id']}," \
                                      f"A," \
                                      f"{self.depth_cache['A'][i][0]}," \
                                      f"{self.depth_cache['A'][i][1]}," \
                                      f"{i + 1}"
                            parsed_data += f"\n{bid_msg}\n{ask_msg}"

                        data_logger.info(parsed_data.strip())
                except Exception as e:
                    logger.error(e)
                    # send alerts to slack / telegram + PagerDuty

    # channel description: https://docs.pro.coinbase.com/#the-level2-channel
    channel = Channel('level2', symbol)
    ws = OrderBookWebSocketClient(loop, channel)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(ws.close())


def collect_coinbase():
    if data_type == "trade":
        coinbase_tick_trade_data()
    elif data_type == "book":
        coinbase_order_book_snapshot()
    else:
        raise ValueError(f"invalid data_type: {data_type}")


if __name__ == "__main__":
    """
    e.g.
    for binance exchange, we want to collect "BTCUSDT", and we want the data to be order book data with depth = 5,
    and we want to collect the data with either 100 ms or 1000 ms refresh rate. we want to save the data in ...
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--exchange", required=True, choices=["coinbase", "binance"])
    parser.add_argument("--symbol", required=True, type=str, help="Format: {base asset}{quote asset} (E.g 'BTCUSDT')")
    parser.add_argument("--data_type", required=True, choices=["trade", "book"],
                        help="tick data data or order book data")
    parser.add_argument("--data_dir", type=str, help="root local data directory", default="./data/")

    args = parser.parse_args()

    symbol = args.symbol.upper()

    exchange_name = args.exchange.lower()
    data_type = args.data_type.lower()

    task_name = f"{exchange_name}_{symbol}_{data_type}"
    logger.debug(f'Collecting {exchange_name} {symbol} Tick {data_type} Data')
    set_logger(args.data_dir)
    loop = asyncio.get_event_loop()
    if exchange_name == "binance":
        loop.run_until_complete(collect_binance())
    elif exchange_name == "coinbase":
        collect_coinbase()

    # ^ [binance and coinbase] add more exchanges in the future
