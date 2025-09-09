from dataclasses import dataclass
from typing import List, Dict, Optional

from asgi.types import HandlerType, Methods, QueryExtractor, BodyExtractor


# this will represent our endpoint/route
@dataclass
class _Route:
    handler: HandlerType
    query_string_extractor: QueryExtractor
    body_extractor: BodyExtractor


# this will make the magic of association between path similarities
class _NodeRoute:
    """
    Visual example
    routes
     -> / -> home handler
     -> /users -> users handler
     -> /files/documents -> documents handler

    root [segment = /, children = Users, Files, handler = home/index handler]

        -> users [segment = users, children = ..., handler =  users handler]

        -> files [segment = files, children = documents, handler =  None]
            -> documents [segment = documents, children = ..., handler =  documents handler]
    ...
    and that continue as required, allowing to add more items and nesting as required
    """
    __slots__ = ["segment", "children", "routes"]

    def __init__(self, segment: str = ""):
        self.segment: str = segment
        self.children: Dict[str, '_NodeRoute'] = {}
        self.routes: Dict[Methods, Optional[_Route]] = {enum_value: None for enum_value in Methods}

    def __repr__(self) -> str:
        return f"NodeRoute({self.segment}) children = {len(self.children)}"


# this will be the interface with our users
class Router:
    __slots__ = ["root"]

    def __init__(self):
        self.root = _NodeRoute()

    @staticmethod
    def get_segments(path: str) -> List[str]:
        return path.split("/")

    def add_route(
            self, 
            path: str, 
            handler: HandlerType, 
            method: Methods = Methods.GET,
            query_string_extractor: QueryExtractor = None,
            body_extractor: BodyExtractor = None,
    ) -> None:
        current = self.root
        segments = self.get_segments(path)
        # insertion DFS like
        for segment in segments:
            if segment not in current.children:
                current.children[segment] = _NodeRoute(segment)

            # swp to the next nest level
            current = current.children[segment]

        current.routes[method] = _Route(handler, query_string_extractor, body_extractor)

    def get_route(self, path: str, method: Methods) -> Optional[_Route]:
        current = self.root
        segments = self.get_segments(path)
        for segment in segments:
            if segment not in current.children:
                return None

            current = current.children[segment]

        # method not allowed
        if current.routes[Methods(method)] is None:
            return None
        return current.routes[Methods(method)]
