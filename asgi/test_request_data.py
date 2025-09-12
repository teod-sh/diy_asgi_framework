import asyncio
import json
import unittest
from typing import Any, NamedTuple, Optional

from asgi.exceptions import InvalidRequestDataException
from asgi.request_data import RequestData

class MockReceiver:
    def __init__(self, payload):
        self.payload = payload
        self.call_count = 0

    async def __call__(self):
        if self.call_count >= len(self.payload):
            return {'body': b'', 'more_body': False}
        self.call_count += 1
        return {'body': self.payload[self.call_count - 1], 'more_body': len(self.payload) >= self.call_count}

async def call_load_stream_data(request_data: RequestData[Any, Any]):
    chunks = []
    async for chunk in request_data.get_stream_body_bytes():
        chunks.append(chunk)
    return chunks


async def call_load_all_body(request_data: RequestData[Any, Any]):
    return await request_data._load_all_body()

async def call_get_json_body(request_data: RequestData[Any, Any]):
    return await request_data.get_json_body()

class TestRequestDataBodyExtraction(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def _run_async_test(self, coro):
        return self.loop.run_until_complete(coro)


class TestGetStreamBodyBytes(TestRequestDataBodyExtraction):

    def test_get_stream_body_bytes_method(self):
        case = NamedTuple("Case", [("receive", MockReceiver), ("expected_chunks", list[Optional[bytes]]), ("description", str)])
        cases = [
            case(receive=MockReceiver([b'test data']), expected_chunks=[b'test data'], description="Single chunk"),
            case(
                receive=MockReceiver([b'test data', b'another chunk']),
                expected_chunks=[b'test data', b'another chunk'],
                description="Multiple chunks"
            ),
            case(receive=MockReceiver([b'']), expected_chunks=[], description="Empty body"),
        ]

        for case in cases:
            with self.subTest(case.description):
                request_data = RequestData(case.receive)
                chunks = self._run_async_test(call_load_stream_data(request_data))
                self.assertEqual(chunks, case.expected_chunks)

    def test_stream_body_bytes_cached_after_first_read(self):
        """Test that subsequent calls return cached body."""
        test_data = [b'test data']
        receive = MockReceiver(test_data)

        request_data = RequestData(receive)

        async def test_logic():
            first_chunks = await call_load_stream_data(request_data)
            second_chunks = await call_load_stream_data(request_data)

            return first_chunks, second_chunks

        first_chunks, second_chunks = self._run_async_test(test_logic())
        self.assertEqual(first_chunks, test_data)
        self.assertEqual(second_chunks, test_data)


class TestLoadAllBody(TestRequestDataBodyExtraction):

    def test_load_all_body_method(self):
        case = NamedTuple("Case", [("receive", MockReceiver), ("expected_body", bytes), ("description", str)])
        cases = [
            case(receive=MockReceiver([b'test data']), expected_body=b'test data', description="Single chunk"),
            case(
                receive=MockReceiver([b'test data', b'another chunk']),
                expected_body=b'test dataanother chunk',
                description="Multiple chunks"
            ),
            case(receive=MockReceiver([b'']), expected_body=b'', description="Empty body"),
        ]

        for case in cases:
            with self.subTest(case.description):
                request_data = RequestData(case.receive)
                body = self._run_async_test(call_load_all_body(request_data))
                self.assertEqual(body, case.expected_body)

    def test_load_all_body_cached(self):
        test_data = [b'cached body']
        receive = MockReceiver(test_data)

        request_data = RequestData(receive)

        async def test_logic():
            body1 = await call_load_all_body(request_data)
            body2 = await call_load_all_body(request_data)
            return body1, body2

        body1, body2 = self._run_async_test(test_logic())
        self.assertEqual(body1, test_data[0])
        self.assertEqual(body2, test_data[0])
        self.assertIs(body1, body2)  # Same object reference


class TestGetJsonBody(TestRequestDataBodyExtraction):

    def test_get_json_body_method(self):
        case = NamedTuple("Case", [("receive", MockReceiver), ("expected_body", Any), ("expected_exception", Any), ("description", str)])
        cases = [
            case(receive=MockReceiver([b'{"key": "value"}']), expected_body={"key": "value"}, expected_exception=None, description="Valid JSON"),
            case(receive=MockReceiver([b'{"invalid": json}']), expected_body=None, expected_exception=InvalidRequestDataException, description="Invalid JSON"),
            case(receive=MockReceiver([b'{"key": "value",', b'"another": "value"}']), expected_body={"key": "value", "another": "value"}, expected_exception=None, description="Multiple chunks"),
            case(receive=MockReceiver([b'']), expected_body={}, expected_exception=None, description="Empty body"),
        ]

        for case in cases:
            with self.subTest(case.description):
                if case.expected_exception is not None:
                    with self.assertRaises(case.expected_exception) as context:
                        request_data = RequestData(case.receive)
                        self._run_async_test(call_get_json_body(request_data))
                        self.assertIsInstance(context.exception, InvalidRequestDataException)

                    continue

                request_data = RequestData(case.receive)
                body = self._run_async_test(call_get_json_body(request_data))
                self.assertEqual(body, case.expected_body)

# fix it
class TestGetBodyWithExtractor(TestRequestDataBodyExtraction):

    def test_get_body_method(self):
        def custom_extractor(body_bytes):
            try:
                return json.loads(body_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                return body_bytes.decode('utf-8')

        case = NamedTuple("Case", [("receive", MockReceiver), ("expected_body", Any), ("custom_extractor", Any), ("description", str)])
        cases = [
            case(receive=MockReceiver([b'test data']), expected_body=None, custom_extractor=None, description="Single chunk"),
            case(receive=MockReceiver([b'{"key": "value"}']), expected_body={"key": "value"}, custom_extractor=custom_extractor, description="Custom extractor"),
            case(receive=MockReceiver([b'{"key": "value",', b'"another": "value"}']), expected_body={"key": "value", "another": "value"}, custom_extractor=custom_extractor, description="Multiple chunks"),
            case(receive=MockReceiver([b'']), expected_body="", custom_extractor=custom_extractor,description="Empty body"),
        ]

        for case in cases:
            with self.subTest(case.description):
                request_data = RequestData(case.receive, body_extractor=case.custom_extractor)
                body = self._run_async_test(request_data.get_body())
                self.assertEqual(body, case.expected_body)
