from abc import ABC
from typing import List, Union

from asgi.types import HandlerType


class BaseGlobalMiddleware(ABC):
    """
    Base class for global middleware.
    You can implement your own global middleware by inheriting this class.

    e.g: CSRF, Cookie, Session middlewares... anything you want to run in a global scope.
    """

    async def __call__(self, call_next: Union['BaseGlobalMiddleware', HandlerType]):
        """
        e.g:
        async def __call__(self, call_next):
            async def wrapper(request_data):
                # do something...
                return await handler(request_data)

        return wrapper
        """
        raise NotImplementedError("__call__ method is not implemented yet")


class _MiddlewareManager:

    def __init__(self, middlewares: List[BaseGlobalMiddleware]):
        self.stack = middlewares

    async def wrap(self, handler: HandlerType, request_data):
        current_handler = handler

        for middleware in reversed(self.stack):
            current_handler = await middleware(current_handler)

        return await current_handler(request_data)

    async def __call__(self, handler, request_data):
        return await self.wrap(handler, request_data)