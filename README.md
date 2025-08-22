This is the skeleton of a WebSockets Client for cTrader's Open API in Python. 

I didn't want to use the SDK (and I can't remember why) and this turned out to be a simple and effective alternative that doesn't add another dependency to your project.

I might or might not implement a package using it in the future. In any case, feel free to make use of this code for you project.

It doesn't use Protobufs because most people just dont need that overhead for maximum performance.The perfomance with JSON is good enough for most.

## How to use

Example of how to use the WebsocketsClientController with FastAPI:

     @app.on_event("startup")
     async def startup_event():
         asyncio.create_task(
             WebsocketsClientController.start_websocket_client_connection_loop()
         )
         logger.info("WebsocketsClientController connection loop task created.")

Later, we simply will use the emitter or receiver of the controller in other parts of the code, like so:

     async def take_entry(self, entry_candle):
         await WebsocketsClientController.client.client_ready_event.wait()

         trade_side = TradeSide.BUY

         await WebsocketsClientController.client.message_emitter.open_trade(
              trade_side, self.robot.id, self.robot.symbol, stop_loss, take_profit

Happy coding and trading!
