import asyncio

import websockets
import websockets.exceptions

from json_client import WebSocketsJsonClient
from logging_config import logger

RECONNECT_DELAY_SECONDS = 5


class WebsocketsClientController:
    client: WebSocketsJsonClient = None

    @classmethod
    async def start_websocket_client_connection_loop(cls):
        if cls.client is None:
            cls.client = WebSocketsJsonClient()

        while True:
            try:
                logger.info("Starting WebSocket client.")
                await cls.client.run_client_and_wait()
            except (
                ConnectionError,
                TimeoutError,
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedOK,
            ) as e:
                logger.warning(
                    f"WebSocket client disconnected or failed: {e}. Attempting to reconnect in {RECONNECT_DELAY_SECONDS} seconds..."
                )
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred in WebSocket client: {e}. Exiting reconnection loop."
                )
                break

    # Example of how to use the WebsocketsClientController with FastAPI:

    # @app.on_event("startup")
    # async def startup_event():
    #     asyncio.create_task(
    #         WebsocketsClientController.start_websocket_client_connection_loop()
    #     )
    #     logger.info("WebsocketsClientController connection loop task created.")

    # Later, we simply will use the emitter or receiver of the controller in other parts of the code, like so:

    # async def take_entry(self, entry_candle):
    #     await WebsocketsClientController.client.client_ready_event.wait()

    #     trade_side = TradeSide.BUY

    #     await WebsocketsClientController.client.message_emitter.open_trade(
    #          trade_side, self.robot.id, self.robot.symbol, stop_loss, take_profit
    #      )
