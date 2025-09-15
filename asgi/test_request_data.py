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

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(_case.receive, headers=[])
                chunks = self._run_async_test(call_load_stream_data(request_data))
                self.assertEqual(chunks, _case.expected_chunks)

    def test_stream_body_bytes_cached_after_first_read(self):
        test_data = [b'test data']
        receive = MockReceiver(test_data)

        request_data = RequestData(receive, headers=[])

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

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(_case.receive, headers=[])
                body = self._run_async_test(call_load_all_body(request_data))
                self.assertEqual(body, _case.expected_body)

    def test_load_all_body_cached(self):
        test_data = [b'cached body']
        receive = MockReceiver(test_data)

        request_data = RequestData(receive, headers=[])

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

        for _case in cases:
            with self.subTest(_case.description):
                if _case.expected_exception is not None:
                    with self.assertRaises(_case.expected_exception) as context:
                        request_data = RequestData(_case.receive, headers=[])
                        self._run_async_test(call_get_json_body(request_data))
                        self.assertIsInstance(context.exception, InvalidRequestDataException)

                    continue

                request_data = RequestData(_case.receive, headers=[])
                body = self._run_async_test(call_get_json_body(request_data))
                self.assertEqual(body, _case.expected_body)


class TestGetBodyWithExtractor(TestRequestDataBodyExtraction):

    def test_get_body_method(self):
        def custom_extractor(body_bytes):
            try:
                return json.loads(body_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                return body_bytes.decode('utf-8')

        case = NamedTuple("Case", [("receive", MockReceiver), ("expected_body", Any), ("custom_extractor", Any), ("description", str)])
        cases = [
            case(receive=MockReceiver([b'test data']), expected_body=None, custom_extractor=None, description="No extractor"),
            case(receive=MockReceiver([b'{"key": "value"}']), expected_body={"key": "value"}, custom_extractor=custom_extractor, description="Custom extractor with JSON"),
            case(receive=MockReceiver([b'{"key": "value",', b'"another": "value"}']), expected_body={"key": "value", "another": "value"}, custom_extractor=custom_extractor, description="Multiple chunks with custom extractor"),
            case(receive=MockReceiver([b'']), expected_body="", custom_extractor=custom_extractor, description="Empty body with custom extractor"),
            case(receive=MockReceiver([b'plain text']), expected_body="plain text", custom_extractor=custom_extractor, description="Plain text with custom extractor"),
        ]

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(_case.receive, headers=[], body_extractor=_case.custom_extractor)
                body = self._run_async_test(request_data.get_body())
                self.assertEqual(body, _case.expected_body)


class TestHeaders(TestRequestDataBodyExtraction):

    def test_get_headers_method(self):
        case = NamedTuple("Case", [("headers", list), ("expected_dict", dict), ("description", str)])
        cases = [
            case(headers=[], expected_dict={}, description="Empty headers"),
            case(
                headers=[(b'content-type', b'application/json')],
                expected_dict={'content-type': 'application/json'},
                description="Single header"
            ),
            case(
                headers=[(b'content-type', b'application/json'), (b'user-agent', b'test-client')],
                expected_dict={'content-type': 'application/json', 'user-agent': 'test-client'},
                description="Multiple headers"
            ),
        ]

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(MockReceiver([b'']), headers=_case.headers)
                headers_dict = self._run_async_test(request_data.get_headers())
                self.assertEqual(headers_dict, _case.expected_dict)

    def test_get_header_value_method(self):
        case = NamedTuple("Case", [("headers", list), ("key", str), ("expected_value", str), ("description", str)])
        cases = [
            case(headers=[], key="content-type", expected_value="", description="Missing header returns empty string"),
            case(
                headers=[(b'content-type', b'application/json')],
                key='content-type',
                expected_value='application/json',
                description="Existing header returns value"
            ),
            case(
                headers=[(b'authorization', b'Bearer token123')],
                key='missing-header',
                expected_value="",
                description="Non-existent header in non-empty headers list"
            ),
        ]

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(MockReceiver([b'']), headers=_case.headers)
                header_value = self._run_async_test(request_data.get_header_value(_case.key))
                self.assertEqual(header_value, _case.expected_value)


class TestQueryString(TestRequestDataBodyExtraction):

    def test_get_query_string_dict_method(self):
        case = NamedTuple("Case", [("query_string", bytes), ("expected_dict", dict), ("description", str)])
        cases = [
            case(query_string=b'', expected_dict={}, description="Empty query string"),
            case(query_string=b'key=value', expected_dict={'key': 'value'}, description="Single parameter"),
            case(
                query_string=b'key1=value1&key2=value2',
                expected_dict={'key1': 'value1', 'key2': 'value2'},
                description="Multiple parameters"
            ),
            case(
                query_string=b'?key1=value1&key2=value2',
                expected_dict={'key1': 'value1', 'key2': 'value2'},
                description="Query string with leading question mark"
            ),
            case(
                query_string=b'key=value1&key=value2',
                expected_dict={'key': ['value1', 'value2']},
                description="Multiple values for same key"
            ),
            case(
                query_string=b'name=John+Doe&age=30',
                expected_dict={'name': 'John Doe', 'age': '30'},
                description="URL encoded values"
            ),
            case(
                query_string=b'malformed&key=value&?another_malformed',
                expected_dict={'key': 'value'},
                description="Malformed parameters are ignored"
            ),
            case(
                query_string=b'empty=&valid=test',
                expected_dict={'empty': '', 'valid': 'test'},
                description="Empty values are preserved"
            ),
        ]

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(MockReceiver([b'']), headers=[], query_string=_case.query_string)
                query_dict = self._run_async_test(request_data.get_query_string_dict())
                self.assertEqual(query_dict, _case.expected_dict)

    def test_get_query_string_with_extractor(self):
        def custom_qs_extractor(qs_bytes):
            return len(qs_bytes)

        def json_qs_extractor(qs_bytes):
            try:
                return json.loads(qs_bytes.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return qs_bytes.decode('utf-8', errors='ignore')

        case = NamedTuple("Case", [("query_string", bytes), ("extractor", Any), ("expected_result", Any), ("description", str)])
        cases = [
            case(query_string=b'', extractor=None, expected_result=None, description="No extractor returns None"),
            case(query_string=b'key=value', extractor=custom_qs_extractor, expected_result=9, description="Custom extractor returns length"),
            case(query_string=b'{"key": "value"}', extractor=json_qs_extractor, expected_result={"key": "value"}, description="JSON extractor with valid JSON"),
            case(query_string=b'invalid json', extractor=json_qs_extractor, expected_result="invalid json", description="JSON extractor with invalid JSON"),
        ]

        for _case in cases:
            with self.subTest(_case.description):
                request_data = RequestData(
                    MockReceiver([b'']),
                    headers=[],
                    query_string=_case.query_string,
                    qs_extractor=_case.extractor
                )
                result = self._run_async_test(request_data.get_query_string())
                self.assertEqual(result, _case.expected_result)
