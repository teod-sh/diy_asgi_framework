from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Union, Dict

class Methods(Enum):
    GET = 0
    POST = 1
    PUT = 2
    PATCH = 3
    DELETE = 4

# this will represent our endpoint/route
@dataclass
class _Route:
    handler: Any
    method: Methods


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
        self.segment: str = segment  # the part of the route we will have
        self.children: Dict[str, _NodeRoute] = {}  # dict segment and its node route
        # self.handler: Any = None  # the handler if exists
        self.routes: Dict = {enum_value: None for enum_value in Methods}

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

    def add_route(self, path: str, handler: Any, method: Methods = Methods.GET) -> None:
        current = self.root
        segments = self.get_segments(path)
        # insertion DFS like
        for segment in segments:
            if segment not in current.children:
                current.children[segment] = _NodeRoute(segment)

            # swp to the next nest level
            current = current.children[segment]

        current.routes[method] = _Route(handler, method)

    def get_route(self, path: str, method: Methods) -> Union[_Route, None]:
        current = self.root
        segments = self.get_segments(path)
        for segment in segments:
            if segment not in current.children:
                # print("not found")
                return None

            current = current.children[segment]

        return current.routes[method]
