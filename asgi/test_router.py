from unittest import TestCase
from .router import Router
from .types import Methods


# Generic handler for most tests - just needs to accept request_data
def generic_handler(request_data):
    return "generic"


# Handler that actually does something for execution test
def echo_handler(request_data):
    return f"received: {request_data}"


# Extractors for testing extractor functionality
def name_query_extractor(params: dict) -> str:
    return params.get("name", "default")


def json_body_extractor(body: bytes) -> dict:
    import json
    return json.loads(body.decode())


def tags_query_extractor(params: dict) -> list:
    return params.get("tags", "").split(",") if params.get("tags") else []


def length_body_extractor(body: bytes) -> int:
    return len(body)


class TestRouter(TestCase):

    def setUp(self):
        self.router = Router()

    def test_get_segments(self):
        batch = [
            ("", ["/"]), # empty path must be handled as root
            ("/", ["/"]), # root
            ("//", ["/"]), # ignore double+ slashes
            ("//////", ["/"]),  # ignore double+ slashes
            ("/api", ["/", "api"]),
            ("/api/v1", ["/", "api", "v1"]),
            ("/api/v1/users", ["/", "api", "v1", "users"]),
            ("/api/v1/users/", ["/", "api", "v1", "users"]), # ignore trailing slash
            ("/api/v1/users/profile", ["/", "api", "v1", "users", "profile"]),
            ("/api/v1/users/profile/", ["/", "api", "v1", "users", "profile"]), # ignore trailing slash
        ]

        for path, segments in batch:
            # print(f"Testing with: {path} expected: {segments}, got: {Router.get_segments(path)}")
            self.assertEqual(Router.get_segments(path), segments)

    def test_basic_route_operations(self):
        """Test basic route addition and retrieval functionality"""
        # Add routes with various paths and methods
        self.router.add_route("/", generic_handler)
        self.router.add_route("/api/v1/users", generic_handler, Methods.POST)
        self.router.add_route("/files/documents/", lambda request_data: "trailing_slash")

        # Validate simple root route
        root_route = self.router.get_route("/", Methods.GET)
        self.assertIsNotNone(root_route)
        self.assertEqual(root_route.handler, generic_handler)

        # Validate complex nested route with specific method
        api_route = self.router.get_route("/api/v1/users", Methods.POST)
        self.assertIsNotNone(api_route)
        self.assertEqual(api_route.handler, generic_handler)

        # Validate trailing slash handling
        trailing_route = self.router.get_route("/files/documents/", Methods.GET)
        self.assertIsNotNone(trailing_route)

    def test_path_segmentation(self):
        """Test path segmentation functionality"""
        # Validate path segmentation
        segments = Router.get_segments("/api/v1/users")
        self.assertEqual(segments, ["", "api", "v1", "users"])

        # Validate empty and root path segmentation
        self.assertEqual(Router.get_segments("/"), ["", ""])
        self.assertEqual(Router.get_segments("users/profile"), ["users", "profile"])

    def test_multiple_methods_same_path(self):
        """Test adding multiple HTTP methods to the same path"""
        base_path = "/api/resource"

        # Add same path with all HTTP methods using the same generic handler
        methods = [Methods.GET, Methods.POST, Methods.PUT, Methods.PATCH, Methods.DELETE]
        for method in methods:
            self.router.add_route(base_path, generic_handler, method)

        # Verify all methods are accessible and not overriding each other
        for method in methods:
            route = self.router.get_route(base_path, method)
            self.assertIsNotNone(route, f"Route not found for method {method}")
            self.assertEqual(route.handler, generic_handler)

    def test_nested_routes_with_different_methods(self):
        """Test nested routes with different HTTP methods"""
        self.router.add_route("/users", generic_handler)
        self.router.add_route("/users/profile", generic_handler, Methods.POST)
        self.router.add_route("/users/settings", generic_handler, Methods.PUT)

        # Verify nested routes with different methods
        self.assertEqual(self.router.get_route("/users", Methods.GET).handler, generic_handler)
        self.assertEqual(self.router.get_route("/users/profile", Methods.POST).handler, generic_handler)
        self.assertEqual(self.router.get_route("/users/settings", Methods.PUT).handler, generic_handler)

        # Verify cross-method isolation
        self.assertIsNone(self.router.get_route("/users/profile", Methods.GET))
        self.assertIsNone(self.router.get_route("/users/settings", Methods.GET))

    def test_query_string_extractor_functionality(self):
        """Test query string extractor functionality"""
        # Add route with query string extractor
        self.router.add_route("/search", generic_handler, Methods.GET, query_string_extractor=name_query_extractor)

        # Get route and verify extractor is stored
        route = self.router.get_route("/search", Methods.GET)
        self.assertIsNotNone(route)
        self.assertEqual(route.handler, generic_handler)
        self.assertEqual(route.query_string_extractor, name_query_extractor)

        # Test extractor functionality
        test_params = {"name": "john", "age": "25"}
        result = route.query_string_extractor(test_params)
        self.assertEqual(result, "john")

    def test_body_extractor_functionality(self):
        """Test body extractor functionality"""
        # Add route with body extractor
        self.router.add_route("/api/data", generic_handler, Methods.POST, body_extractor=json_body_extractor)

        # Get route and verify extractor is stored
        route = self.router.get_route("/api/data", Methods.POST)
        self.assertIsNotNone(route)
        self.assertEqual(route.handler, generic_handler)
        self.assertEqual(route.body_extractor, json_body_extractor)

        # Test extractor functionality
        test_body = b'{"name": "test", "value": 42}'
        result = route.body_extractor(test_body)
        self.assertEqual(result, {"name": "test", "value": 42})

    def test_combined_extractors(self):
        """Test routes with both query string and body extractors"""
        # Add route with both extractors
        self.router.add_route(
            "/api/upload",
            generic_handler,
            Methods.PUT,
            query_string_extractor=tags_query_extractor,
            body_extractor=length_body_extractor
        )

        # Get route and verify both extractors are stored
        route = self.router.get_route("/api/upload", Methods.PUT)
        self.assertIsNotNone(route)
        self.assertEqual(route.handler, generic_handler)
        self.assertEqual(route.query_string_extractor, tags_query_extractor)
        self.assertEqual(route.body_extractor, length_body_extractor)

        # Test both extractors
        test_params = {"tags": "python,web,api"}
        test_body = b'{"data": "test content"}'

        query_result = route.query_string_extractor(test_params)
        body_result = route.body_extractor(test_body)

        self.assertEqual(query_result, ["python", "web", "api"])
        self.assertEqual(body_result, 24)

    def test_route_not_found(self):
        """Test behavior when routes are not found"""
        self.router.add_route("/existing", generic_handler, Methods.GET)

        # Test non-existent path
        self.assertIsNone(self.router.get_route("/nonexistent", Methods.GET))

        # Test existing path with wrong method
        self.assertIsNone(self.router.get_route("/existing", Methods.POST))

    def test_default_parameters(self):
        """Test default parameter values"""
        # Add route with default parameters (GET method, no extractors)
        self.router.add_route("/default", generic_handler)

        route = self.router.get_route("/default", Methods.GET)
        self.assertIsNotNone(route)
        self.assertEqual(route.handler, generic_handler)
        self.assertIsNone(route.query_string_extractor)
        self.assertIsNone(route.body_extractor)

    def test_handler_execution(self):
        """Test that handlers can be called with test data"""
        self.router.add_route("/echo", echo_handler, Methods.POST)

        route = self.router.get_route("/echo", Methods.POST)
        self.assertIsNotNone(route)

        # Test calling the handler with mock data
        mock_request = "test_request_data"
        result = route.handler(mock_request)
        self.assertEqual(result, "received: test_request_data")