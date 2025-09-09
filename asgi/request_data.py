from typing import Generic, Union

from asgi.types import BODY_TYPE, QUERY_STRING_TYPE, QueryExtractor, BodyExtractor


class RequestData(Generic[QUERY_STRING_TYPE, BODY_TYPE]):  # contract

    def __init__(self, qs_extractor: QueryExtractor = None, body_extractor: BodyExtractor = None):
        self.qs_extractor = qs_extractor
        self.body_extractor = body_extractor

    async def get_query_string_params(self) -> Union[QUERY_STRING_TYPE, None]:
        if self.qs_extractor is None:
            return None
        return self.qs_extractor({})

    async def get_body_bytes(self) -> bytes:
        ...

    async def get_json_body(self) -> dict:
        ...

    async def get_body(self) -> Union[BODY_TYPE, None]:
        if self.body_extractor is None:
            return None
        return self.body_extractor(b'')

    async def get_headers(self) -> dict:
        ...

    async def get_header_value(self, key: str) -> str:
        ...
