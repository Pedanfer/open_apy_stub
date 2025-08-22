import asyncio
import traceback

import websockets
import websockets.client
import websockets.exceptions

from logging_config import logger

from .message_emitter import MessageEmitter
from .message_receiver import MessageReceiver
from .models import ClientAssignables, WebsocketClientEvents

CLIENT_ID = ""
CLIENT_SECRET = ""
REFRESH_TOKEN = ""
ACCESS_TOKEN = ""
API_HOST_DEMO = "demo.ctraderapi.com"
API_PORT_DEMO = 5036


class WebSocketsJsonClient:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.assignables = ClientAssignables(access_token=ACCESS_TOKEN)
        self.websocket: websockets.client.WebSocketClientProtocol = None
        self.events: WebsocketClientEvents = WebsocketClientEvents()
        self.message_emitter: MessageEmitter = None
        self.message_receiver: MessageReceiver = None
        self.client_ready_event = asyncio.Event()
        self.fx_pairs_ids = {}
        self._receiver_task = None
        self._heartbeat_task = None

    async def _authenticate_and_initialize(self):
        await self.message_emitter.request_application_auth(
            self.client_id, self.client_secret
        )
        await self.events.app_auth.wait()
        logger.info("Application authentication confirmed.")

        await self.events.account_auth.wait()
        logger.info("Account authentication confirmed.")

        await self.message_emitter.get_symbols_list(self.assignables.account_id)
        self.client_ready_event.set()

    async def _cleanup_tasks(self):
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        if self.websocket and not self.websocket.closed:
            await self.websocket.close()

    async def run_client_and_wait(self):
        uri = f"wss://{API_HOST_DEMO}:{API_PORT_DEMO}"
        logger.info(f"Connecting to {uri}...")

        try:
            async with websockets.client.connect(uri, ssl=True) as ws:
                self.websocket = ws
                self.set_up_communication(ws)
                await self._authenticate_and_initialize()

                # Keep the connection alive indefinitely until it closes or an error occurs
                await ws.wait_closed()

        except websockets.exceptions.ConnectionClosedOK:
            logger.info("WebSocket connection closed normally in run_client_and_wait.")
            raise
        except asyncio.CancelledError:
            logger.info("run_client_and_wait task was cancelled.")
            raise
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(
                f"WebSocket connection closed with an error (server disconnected unexpectedly): {e}"
            )
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred in run_client_and_wait: {e}")
            traceback.print_exc()
            raise
        finally:
            await self._cleanup_tasks()
            logger.info("Disconnected from cTrader's websockets server.")

    def set_up_communication(self, ws: websockets.client.WebSocketClientProtocol):
        self.message_emitter = MessageEmitter(ws, self.assignables, self.events)
        self.message_receiver = MessageReceiver(
            self.events, ws, self.message_emitter, self.assignables
        )
        self._receiver_task = asyncio.create_task(
            self.message_receiver.receive_messages()
        )
        self._heartbeat_task = asyncio.create_task(
            self.message_emitter.heartbeat_sender()
        )
