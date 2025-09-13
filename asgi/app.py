import asyncio
from typing import List, Dict, Any, Callable, Awaitable

from asgi.background_tasks import _create_background_tasks_instance
from asgi.exceptions import InvalidRequest
from asgi.http_responses import (
    NOT_FOUND_TEXTResponse,
    INTERNAL_SERVER_ERROR_TEXTResponse,
    BaseHTTPResponse,
    _ResponseData
)
from asgi.request_data import RequestData
from asgi.router import Router
from asgi.api_router import ApiRouter


# ASGI type aliases
ASGIScope = Dict[str, Any]
ASGIReceive = Callable[[], Awaitable[Dict[str, Any]]]
ASGISend = Callable[[Dict[str, Any]], Awaitable[None]]


class App:

    def __init__(self, max_running_tasks: int = 2):
        self._router = None
        self._bg_tasks = _create_background_tasks_instance(max_running_tasks=max_running_tasks)

    def include_routes(self, routes: List[ApiRouter]) -> None:
        """
        This method will add all registered routes to the application router.
        It should be called at the application startup.
        Call it twice will raise an error.

        e.g:
        # pkg1
        router_1 = ApiRouter()
        @router_1.get("/home")
        async def home(request_data):
            print("home triggered")

        @router_1.get("/")
        async def root(request_data):
            print("root triggered")

        # pkg2
        router_2 = ApiRouter()
        @router_2.get("/about")
        async def about(request_data):
            print("about triggered")

        # main
        app = App()
        app.include_routes([router_1, router_2])
        """
        assert self._router is None, "include_routes method can be called only once"

        self._router = Router()

        route_list = []
        for router_items in routes:
            route_list += router_items.routes

        sorted_routes = sorted(route_list, key=lambda x: x[0])
        for route in sorted_routes:
            self._router.add_route(*route)

    async def __call__(self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend):
        if scope['type'] == 'http':
            return await self._handle_http_request(scope, receive, send)

        if scope["type"] == "lifespan":
            return await self._handle_lifespan(receive, send)

        return None

    async def _handle_lifespan(
            self, receive: Callable[[], Awaitable[dict[str, Any]]],
            send: Callable[[dict[str, Any]], Awaitable[None]]
    ):
        async def run_bg_tasks():
            while True:
                await self._bg_tasks.run_tasks()
                await asyncio.sleep(0.5)

        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                asyncio.create_task(run_bg_tasks())
                await send({"type": "lifespan.startup.complete"})

            elif message["type"] == "lifespan.shutdown":
                await self._bg_tasks.shutdown()
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def _handle_http_request(self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend):
        assert scope['type'] == 'http'
        response_data = await self._run_http_handler(scope['path'], scope['method'], receive)
        await self._send_http_response(response_data, send)

    async def _run_http_handler(self, path: str, method: str, receive: ASGIReceive) -> _ResponseData:
        try:
            target = self._router.get_route(path, method)
            if target is None:
                return await NOT_FOUND_TEXTResponse()()

            request_data = RequestData(receive, target.query_string_extractor, target.body_extractor)
            response = await target.handler(request_data)
            if response is not isinstance(response, BaseHTTPResponse):
                print('handler returned a non valid response. Response must be an instance of BaseHTTPResponse')
                return await INTERNAL_SERVER_ERROR_TEXTResponse()()

            return await response()

        except InvalidRequest as e:
             return await e.http_response()

        except Exception as e:
            print('error' + str(e))
            return await INTERNAL_SERVER_ERROR_TEXTResponse()()

    @staticmethod
    async def _send_http_response(resp: _ResponseData, send: ASGISend):
        await send({
            "type": "http.response.start",
            "status": resp.status_code,
            "headers": resp.headers
        })

        await send({
            "type": "http.response.body",
            "body": resp.body
        })