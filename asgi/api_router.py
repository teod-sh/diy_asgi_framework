from typing import List, Tuple, Callable

from asgi.types import HandlerType, Methods, QueryExtractor, BodyExtractor

RouteInfo = Tuple[str, HandlerType, Methods, QueryExtractor, BodyExtractor]
DecoratorReturn = Callable[[HandlerType], HandlerType]


class ApiRouter:

    __slots__ = ["routes"]

    def __init__(self):
        self.routes: List[RouteInfo] = []

    def decorator(
            self, 
            path: str,
            method: Methods,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        def wrap(handler: HandlerType) -> HandlerType:
            self.routes.append((path, handler, method, query_string_extractor, body_extractor))
            return handler
        return wrap

    def get(
            self, 
            path: str,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        return self.decorator(path, Methods.GET, query_string_extractor, body_extractor)

    def post(
            self, 
            path: str,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        return self.decorator(path, Methods.POST, query_string_extractor, body_extractor)

    def delete(
            self, 
            path: str,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        return self.decorator(path, Methods.DELETE, query_string_extractor, body_extractor)

    def patch(
            self, 
            path: str,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        return self.decorator(path, Methods.PATCH, query_string_extractor, body_extractor)

    def put(
            self, 
            path: str,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        return self.decorator(path, Methods.PUT, query_string_extractor, body_extractor)

    def multi_methods(
            self, 
            path: str,
            methods: List[Methods],
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None
    ) -> DecoratorReturn:
        def decorator(handler: HandlerType) -> HandlerType:
            for method in methods:
                self.routes.append((path, handler, method, query_string_extractor, body_extractor))
            return handler
        return decorator
