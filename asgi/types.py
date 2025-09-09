from enum import Enum
from typing import Callable, TypeVar, Optional

BODY_TYPE = TypeVar('BODY_TYPE')
QUERY_STRING_TYPE = TypeVar('QUERY_STRING_TYPE')
HandlerType = Callable[['RequestData[QUERY_STRING_TYPE, BODY_TYPE]'], None]
QueryExtractor = Optional[Callable[[dict], QUERY_STRING_TYPE]]
BodyExtractor = Optional[Callable[[bytes], BODY_TYPE]]

class Methods(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
