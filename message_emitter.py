import asyncio
import datetime
import json
import re

import pytz
import websockets.client

from logging_config import logger

from .models import (
    PAYLOAD_TYPES,
    ClientAssignables,
    LotSize,
    TradeSide,
    WebsocketClientEvents,
)


class MessageEmitter:
    def __init__(
        self,
        websocket: websockets.client.WebSocketClientProtocol,
        client_assignables: ClientAssignables,
        events: WebsocketClientEvents,
    ):
        self.websocket = websocket
        self.client_assignables = client_assignables
        self.events = events

    def generate_client_msg_id(self, payload_type: int) -> str:
        now = datetime.datetime.now(pytz.utc)
        timestamp_str = now.isoformat()
        return f"{payload_type}-{timestamp_str}"

    async def send_message(self, payload_type: int, payload: dict) -> str:
        client_msg_id = self.generate_client_msg_id(payload_type)
        message = {
            "clientMsgId": client_msg_id,
            "payloadType": payload_type,
            "payload": payload,
        }
        json_message = json.dumps(message, indent=4)
        if payload_type != PAYLOAD_TYPES.PROTO_HEARTBEAT_EVENT:
            logger.info(f"SENDING: {json_message}")
        await self.websocket.send(json_message)
        return client_msg_id

    async def heartbeat_sender(self):
        try:
            while True:
                await asyncio.sleep(30)
                if self.websocket and not self.websocket.closed:
                    await self.send_heartbeat_message()
        except asyncio.CancelledError:
            logger.info("Heartbeat sender stopped.")
        except Exception as e:
            logger.info(f"Heartbeat sender error: {e}")

    async def request_application_auth(self, client_id: str, client_secret: str):
        await self.send_message(
            PAYLOAD_TYPES.PROTO_OA_APPLICATION_AUTH_REQ,
            {"clientId": client_id, "clientSecret": client_secret},
        )

    async def send_heartbeat_message(self, msg=None):
        await self.send_message(PAYLOAD_TYPES.PROTO_HEARTBEAT_EVENT, {})

    async def request_account_auth(self):
        await self.send_message(
            PAYLOAD_TYPES.PROTO_OA_ACCOUNT_AUTH_REQ,
            {
                "accessToken": self.client_assignables.access_token,
                "ctidTraderAccountId": self.client_assignables.account_id,
            },
        )

    async def get_symbols_list(
        self,
        account_id: int,
    ):
        logger.info(f"Requesting symbols list for account: {account_id}")
        await self.send_message(
            PAYLOAD_TYPES.PROTO_OA_SYMBOLS_LIST_REQ,
            {
                "ctidTraderAccountId": self.client_assignables.account_id,
                "includeArchivedSymbols": True,
            },
        )
        await self.events.symbols_list.wait()
        logger.info("Symbols list requested and processed.")

    async def open_trade(
        self,
        trade_side: TradeSide,
        symbol_name: str,
        stop_loss: float,
        take_profit: float,
    ) -> str:
        normalized_symbol = re.sub(r"[/-]", "", symbol_name)
        symbol_id = self.client_assignables.fx_pairs_ids[normalized_symbol]
        payload = {
            "ctidTraderAccountId": self.client_assignables.account_id,
            "symbolId": symbol_id,
            "tradeSide": trade_side.value,
            "volume": LotSize.MICRO_LOT.value,
            "orderType": "MARKET",
            "relativeStopLoss": stop_loss,
            "relativeTakeProfit": take_profit,
        }

        return await self.send_message(PAYLOAD_TYPES.PROTO_OA_NEW_ORDER_REQ, payload)

    async def close_position(self, position_id: int) -> str:
        payload = {
            "ctidTraderAccountId": self.client_assignables.account_id,
            "positionId": position_id,
            "volume": LotSize.MICRO_LOT.value,
        }

        return await self.send_message(
            PAYLOAD_TYPES.PROTO_OA_CLOSE_POSITION_REQ, payload
        )

    async def amend_position_sl(
        self,
        new_stop_loss: float,
        position_id: int,
        same_take_profit: float,
    ) -> str:
        payload = {
            "ctidTraderAccountId": self.client_assignables.account_id,
            "positionId": position_id,
            "stopLoss": new_stop_loss,
            "takeProfit": same_take_profit,
        }
        return await self.send_message(
            PAYLOAD_TYPES.PROTO_OA_AMEND_POSITION_SLTP_REQ, payload
        )
