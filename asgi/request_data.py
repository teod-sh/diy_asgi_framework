import json
from typing import Generic, Union, AsyncGenerator, Any, Callable, Awaitable, Dict

from asgi.exceptions import InvalidRequestDataException
from asgi.types import BODY_TYPE, QUERY_STRING_TYPE, QueryExtractor, BodyExtractor


class RequestData(Generic[QUERY_STRING_TYPE, BODY_TYPE]):

    def __init__(self, asgi_receiver_method: Callable[[], Awaitable[Dict[str, Any]]],  qs_extractor: QueryExtractor = None, body_extractor: BodyExtractor = None):
        self._qs_extractor = qs_extractor
        self._body_extractor = body_extractor
        self._asgi_receiver_method = asgi_receiver_method

        self._body = b''

    async def get_query_string_params(self) -> Union[QUERY_STRING_TYPE, None]:
        if self._qs_extractor is None:
            return None
        return self._qs_extractor({})

    async def get_stream_body_bytes(self) -> AsyncGenerator[bytes, None]:
        """
        Streams the request body bytes. Can only be called once per request.
        After the first complete iteration, subsequent calls will yield the cached body.

        Note: This follows ASGI spec where the receiver callable is exhausted after
        the first complete read.
        """
        if self._body:
            yield self._body
            return

        has_more_data = True
        while has_more_data:
            message = await self._asgi_receiver_method()

            data = message.get('body', b'')
            if not data:
                break

            self._body += data
            yield data
            has_more_data = message.get('more_body', False)

    async def _load_all_body(self) -> bytes:
        if self._body:
            return self._body

        async for _ in self.get_stream_body_bytes():
            pass

        return self._body

    async def get_json_body(self) -> dict:
        """
        Parse the request body as JSON.
        Raises ValueError if body is empty or contains invalid JSON.

        !Important: it won't trigger custom extractors as body_extractor is not used
        """
        body = await self._load_all_body()
        try:
            if not body:
                return {}
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise InvalidRequestDataException(f"Invalid JSON body: {e}")

    async def get_body(self) -> Union[BODY_TYPE, None]:
        """
        This method will trigger custom extractors registered withing the router
        The type of the returned value depends on the body_extractor used.

        If no extractor is registered, returns None.
        """
        if self._body_extractor is None:
            return None

        body = await self._load_all_body()
        return self._body_extractor(body)

    async def get_headers(self) -> dict:
        ...

    async def get_header_value(self, key: str) -> str:
        ...
