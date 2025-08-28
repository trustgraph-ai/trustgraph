
import asyncio
from aiohttp import web, WSMsgType
import logging

from .. running import Running

logger = logging.getLogger("socket")
logger.setLevel(logging.INFO)

class SocketEndpoint:

    def __init__(
            self, endpoint_path, auth, dispatcher,
    ):

        self.path = endpoint_path
        self.auth = auth
        self.operation = "socket"

        self.dispatcher = dispatcher

    async def worker(self, ws, dispatcher, running):

        await dispatcher.run()

    async def listener(self, ws, dispatcher, running):
        """Enhanced listener with graceful shutdown"""
        try:
            async for msg in ws:
                # On error, finish
                if msg.type == WSMsgType.TEXT:
                    await dispatcher.receive(msg)
                    continue
                elif msg.type == WSMsgType.BINARY:
                    await dispatcher.receive(msg)
                    continue
                else:
                    # Graceful shutdown on close
                    logger.info("Websocket closing, initiating graceful shutdown")
                    running.stop()
                    
                    # Allow time for dispatcher cleanup
                    await asyncio.sleep(1.0)
                    
                    # Close websocket if not already closed
                    if not ws.closed:
                        await ws.close()
                    break
            else:
                # This executes when the async for loop completes normally (no break)
                logger.debug("Websocket iteration completed, performing cleanup")
                running.stop()
                if not ws.closed:
                    await ws.close()
        except Exception:
            # Handle exceptions and cleanup
            running.stop()
            if not ws.closed:
                await ws.close()
            raise
        
    async def handle(self, request):
        """Enhanced handler with better cleanup"""
        try:
            token = request.query['token']
        except:
            token = ""

        if not self.auth.permitted(token, self.operation):
            return web.HTTPUnauthorized()
        
        # 50MB max message size
        ws = web.WebSocketResponse(max_msg_size=52428800)

        await ws.prepare(request)
        
        dispatcher = None
        
        try:

            async with asyncio.TaskGroup() as tg:

                running = Running()

                dispatcher = await self.dispatcher(
                    ws, running, request.match_info
                )

                worker_task = tg.create_task(
                    self.worker(ws, dispatcher, running)
                )

                lsnr_task = tg.create_task(
                    self.listener(ws, dispatcher, running)
                )

                logger.debug("Created task group, waiting for completion...")

                # Wait for threads to complete

            logger.debug("Task group closed")

        except ExceptionGroup as e:

            logger.error("Exception group occurred:", exc_info=True)

            for se in e.exceptions:
                logger.error(f"  Exception type: {type(se)}")
                logger.error(f"  Exception: {se}")
                
            # Attempt graceful dispatcher shutdown
            if dispatcher and hasattr(dispatcher, 'destroy'):
                try:
                    await asyncio.wait_for(
                        dispatcher.destroy(), 
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Dispatcher shutdown timed out")
                except Exception as de:
                    logger.error(f"Error during dispatcher cleanup: {de}")
                    
        except Exception as e:
            logger.error(f"Socket exception: {e}", exc_info=True)
            
        finally:
            # Ensure dispatcher cleanup
            if dispatcher and hasattr(dispatcher, 'destroy'):
                try:
                    await dispatcher.destroy()
                except Exception as de:
                    logger.error(f"Error in final dispatcher cleanup: {de}")
                    
            # Ensure websocket is closed
            if ws and not ws.closed:
                await ws.close()
                
        return ws

    async def start(self):
        pass

    async def stop(self):
        self.running.stop()

    def add_routes(self, app):

        app.add_routes([
            web.get(self.path, self.handle),
        ])

