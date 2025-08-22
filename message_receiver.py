import json

import websockets.client
import websockets.exceptions

from logging_config import logger

from .message_emitter import MessageEmitter
from .models import (
    PAYLOAD_TYPES,
    ClientAssignables,
    ProtoOAExecutionType,
    WebsocketClientEvents,
)

FOREX_PAIRS = [
    "CADJPY",
    "GBPCAD",
    "EURUSD",
    "GBPUSD",
    "GBPJPY",
    "EURCAD",
    "NZDJPY",
    "EURJPY",
    "AUDJPY",
    "USDJPY",
    "NZDCAD",
    "NZDUSD",
    "AUDUSD",
    "GBPAUD",
]


class MessageReceiver:
    def __init__(
        self,
        events: WebsocketClientEvents,
        websocket: websockets.client.WebSocketClientProtocol,
        emitter: MessageEmitter,
        client_assignables: ClientAssignables,
    ):
        self.websocket = websocket
        self.events = events
        self.handlers = {}
        self.emitter = emitter
        self.client_assignables = client_assignables
        self.register_all_handlers()

    def register_all_handlers(self):
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_APPLICATION_AUTH_RES,
            self.handle_application_auth_res,
        )
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_ACCOUNT_AUTH_RES, self.handle_account_auth_res
        )
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_RES,
            self.handle_get_accounts_by_access_token_res,
        )
        self.register_handler(PAYLOAD_TYPES.PROTO_OA_ERROR_RES, self.handle_error_res)
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_EXECUTION_EVENT, self.handle_execution_event
        )
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_ORDER_ERROR_EVENT, self.handle_order_error_event
        )
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_SYMBOLS_LIST_RES, self.handle_symbols_list_res
        )
        self.register_handler(
            PAYLOAD_TYPES.PROTO_OA_ACCOUNT_DISCONNECT_EVENT,
            self.handle_account_disconnection,
        )
        self.register_handler(
            PAYLOAD_TYPES.PROTO_HEARTBEAT_EVENT, self.emitter.send_heartbeat_message
        )

    async def receive_messages(self):
        try:
            async for message in self.websocket:
                try:
                    msg = json.loads(message)
                    payload_type = msg.get("payloadType")
                    handler = self.handlers.get(payload_type)

                    if payload_type != 51 and not handler:
                        logger.info(
                            f"RECEIVED message from Open API of unknown type: {json.dumps(msg, indent=2)}"
                        )

                    if handler:
                        await handler(msg)

                except json.JSONDecodeError as e:
                    logger.info(f"Failed to parse message: {e}")
        except websockets.exceptions.ConnectionClosedOK:
            print("WebSocket connection closed normally.")
        except Exception as e:
            print(f"Receiving websockets messages error: {e}")
            self.events.clear_all()

    def register_handler(self, payload_type, handler_func):
        self.handlers[payload_type] = handler_func

    async def handle_application_auth_res(self, msg):
        self.events.app_auth.set()
        await self.emitter.send_message(
            PAYLOAD_TYPES.PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_REQ,
            {
                "accessToken": self.client_assignables.access_token,
            },
        )

    async def handle_account_auth_res(self, msg: dict):
        account_id_res = msg.get("payload", {}).get("ctidTraderAccountId")
        if account_id_res:
            logger.info(f"Account {account_id_res} authenticated!")
            self.events.account_auth.set()
        else:
            logger.info("Account authentication response missing ctidTraderAccountId.")
            self.events.account_auth.set()

    async def handle_get_accounts_by_access_token_res(self, msg: dict):
        accounts = msg.get("payload", {}).get("ctidTraderAccount", [])

        for account in accounts:
            is_live = account.get("isLive", False)
            account_id = account.get("ctidTraderAccountId")

            if not is_live:
                self.client_assignables.account_id = account_id
                await self.emitter.request_account_auth()
                break

    async def handle_account_disconnection(self, msg: dict):
        self.events.account_auth.clear()
        await self.emitter.request_account_auth()

    async def handle_symbols_list_res(self, msg: dict):
        symbols = msg.get("payload", {}).get("symbol", [])

        # Look for active symbols
        for symbol in symbols:
            symbol_id = symbol.get("symbolId")
            symbol_name: str = symbol.get("symbolName")

            if symbol_name in FOREX_PAIRS:
                self.client_assignables.fx_pairs_ids[symbol_name] = symbol_id

        self.events.symbols_list.set()

    async def handle_error_res(self, msg: dict):
        error_code = msg.get("payload", {}).get("errorCode", "UNKNOWN_ERROR")
        description = msg.get("payload", {}).get(
            "description", "No description available."
        )
        account_id_err = msg.get("payload", {}).get("ctidTraderAccountId")
        account_info = f" for account {account_id_err}" if account_id_err else ""

        logger.info(f"ERROR{account_info}: {error_code} - {description}")

        # Crucially, unblock any waiting events in case an error prevents them from being set by their specific handlers
        self.events.app_auth.set()
        self.events.account_auth.set()
        self.events.symbols_list.set()

    async def handle_execution_event(self, msg: dict):
        payload = msg.get("payload", {})

        execution_type = payload.get("executionType", {})

        if (
            execution_type != ProtoOAExecutionType.ACCEPTED.value
            and execution_type != ProtoOAExecutionType.FILLED.value
        ):
            logger.info(
                f"Received message of not accepted or filled execution type: \n{json.dumps(payload, indent=2)}"
            )
            return

        position = payload.get("position")

        position_status = position.get("positionStatus")

        is_closed = position_status == 2
        is_open = position_status == 1

        profit_usd = 0

        if is_open:
            # Store the position id somewhere for later use
            logger.info("Position opened.")

        elif is_closed:
            deal = payload.get("deal")

            close_position = deal.get("closePositionDetail", {})
            gross_profit = close_position.get("grossProfit", 0)
            commission = close_position.get("commission", 0)

            # The profit and commission come in cents
            profit_usd = (gross_profit + commission) / 100

            logger.info(f"Position closed.\nProfit/Loss: {profit_usd} USD")

    async def handle_order_error_event(self, msg: dict):
        payload = msg.get("payload", {})

        error_code = payload.get("errorCode", "UNKNOWN_ERROR")
        order_id = payload.get("orderId", "N/A")
        description = payload.get("description", "No description provided.")

        logger.info("\n--- Order Error Event ---")
        logger.info(f"  Order ID: {order_id}")
        logger.info(f"  Error Code: {error_code}")
        logger.info(f"  Description: {description}")
        logger.info("-------------------------\n")
