from typing import List, Dict, Any, Callable, Awaitable


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

    def __init__(self):
        self.router = None

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
        assert self.router is None, "include_routes method can be called only once"

        self.router = Router()

        route_list = []
        for router_items in routes:
            route_list += router_items.routes

        sorted_routes = sorted(route_list, key=lambda x: x[0])
        for route in sorted_routes:
            self.router.add_route(*route)

    async def __call__(self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend):
        if scope['type'] == 'http':
            return await self._handle_http_request(scope, receive, send)

        # we will deal with other types later

    async def _handle_http_request(self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend):
        ''' payload ref
        scope = {
            'type': 'http',
            'asgi': {'version': '3.0', 'spec_version': '2.3'},
            'http_version': '1.1', 'server': ('127.0.0.1', 8000),
            'client': ('127.0.0.1', 51945), 'scheme': 'http',
            'method': 'GET', 'root_path': '',
            'path': '/some-path/', 'raw_path': b'/some-path/',
            'query_string': b'qs1=1&qs2=opa!',
            'headers': [
                (b'user-agent', b'PostmanRuntime/7.45.0'),
                (b'accept', b'*/*'),
                (b'postman-token', b'1111f6f3-1111-1111-1111-37150dd41111'),
                (b'host', b'localhost:8000'),
                (b'accept-encoding', b'gzip, deflate, br'),
                (b'connection', b'keep-alive')
            ],
            'state': {}
        }
        '''
        assert scope['type'] == 'http'
        response_data = await self._run_http_handler(scope['path'], scope['method'], receive)
        await self._send_http_response(response_data, send)

    async def _run_http_handler(self, path: str, method: str, receive: ASGIReceive) -> _ResponseData:
        try:
            target = self.router.get_route(path, method)
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