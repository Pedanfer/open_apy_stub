import asyncio
from enum import Enum


class WebsocketClientEvents:
    app_auth: asyncio.Event
    account_auth: asyncio.Event
    symbols_list: asyncio.Event    

    def clear_all(self):
        self.app_auth.clear()
        self.account_auth.clear()
        self.symbols_list.clear()      

    def __init__(self):
        self.app_auth = asyncio.Event()
        self.account_auth = asyncio.Event()
        self.symbols_list = asyncio.Event()

class ClientAssignables:
    def __init__(self, access_token):
        self.access_token = access_token
        self.account_id = None
        self.fx_pairs_ids = {}


class PAYLOAD_TYPES:
    # Core Communication
    PROTO_HEARTBEAT_EVENT = 51
    PROTO_OA_ERROR_RES = 2142
    PROTO_OA_SYMBOLS_LIST_REQ = 2114
    PROTO_OA_SYMBOLS_LIST_RES = 2115

    # Application and Account Authentication
    PROTO_OA_APPLICATION_AUTH_REQ = 2100
    PROTO_OA_APPLICATION_AUTH_RES = 2101
    PROTO_OA_ACCOUNT_AUTH_REQ = 2102
    PROTO_OA_ACCOUNT_AUTH_RES = 2103

    # Account Listing
    PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_REQ = 2149
    PROTO_OA_GET_ACCOUNTS_BY_ACCESS_TOKEN_RES = 2150

    # Trading Operations
    PROTO_OA_NEW_ORDER_REQ = 2106
    PROTO_OA_AMEND_POSITION_SLTP_REQ = 2110
    PROTO_OA_CLOSE_POSITION_REQ = 2111
    PROTO_OA_ACCOUNT_DISCONNECT_EVENT = 2164

    # Trading Events
    PROTO_OA_ORDER_ERROR_EVENT = 2132
    PROTO_OA_EXECUTION_EVENT = 2126


class LotSize(Enum):
    """
    Represents common forex lot sizes converted for the cTrader Open API 'volume' field.
    The API requires volume to be represented in 0.01 of a unit (i.e., actual units * 100).
    """

    STANDARD_LOT = 10_000_000
    MINI_LOT = 1_000_000
    MICRO_LOT = 100_000
    NANO_LOT = 10_000


class TradeSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class ProtoOAExecutionType(Enum):
    ACCEPTED = 2
    FILLED = 3
    CANCELLED = 5
