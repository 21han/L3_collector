# if __name__ == "__main__":
#     import sys
#     import time
#     from clients.coinbase import WebsocketClient
#     from loguru import logger
#
#
#     class MyWebsocketClient(WebsocketClient):
#         def on_open(self):
#             self.url = "wss://ws-feed.pro.coinbase.com/"
#
#         def on_message(self, msg):
#             logger.info(msg)
#             if msg['type'] == "snapshot":
#                 logger.debug(f"bid size: {len(msg['bids'])}, ask size: {len(msg['asks'])}")
#                 logger.debug(f"{msg['bids'][:10]}, {msg['bids'][-10:]}")
#                 time.sleep(10)
#
#         def on_close(self):
#             print("-- Goodbye! --")
#
#
#     wsClient = MyWebsocketClient(channels=['matches'], products=['BTC-USD'], verbose=False)
#     wsClient.start()
#     print(wsClient.url, wsClient.products)
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         wsClient.close()
#
#     if wsClient.error:
#         sys.exit(1)
#     else:
#         sys.exit(0)


import asyncio



loop = asyncio.get_event_loop()

from copra.websocket import Channel, Client
channel = Channel('matches', 'LTC-USD')
ws = Client(loop, channel)

try:
    loop.run_forever()
except KeyboardInterrupt:
    loop.run_until_complete(ws.close())
    loop.close()
