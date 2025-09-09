from typing import List

from asgi.request_data import RequestData
from asgi.router import Router
from asgi.api_router import ApiRouter


class App:

    def __init__(self):
        self.router = None

    def include_routes(self, routes: List[ApiRouter]) -> None:
        if self.router is not None:
            return

        self.router = Router()

        route_list = []
        for router_items in routes:
            route_list += router_items.routes

        sorted_routes = sorted(route_list, key=lambda x: x[0])
        for route in sorted_routes:
            self.router.add_route(*route)


    async def __call__(self, scope, receive, send):
        target = self.router.get_route(scope['path'], scope['method'])

        if target is None:
            await send({"type": "http.response.start", "status": 404})
            await send({"type": "http.response.body", "body": b"not found"})
            return

        request_data = RequestData(target.query_string_extractor, target.body_extractor)
        await target.handler(request_data)
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"ok"})