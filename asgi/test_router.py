from unittest import TestCase
from .router import Router, Methods


class TestRouter(TestCase):

    def setUp(self):
        self.router = Router()

    def test_add_route(self):
        # Test handlers for different scenarios
        def simple_handler():
            return "simple"
        
        def complex_handler():
            return "complex"
        
        # Add routes with various paths and methods
        self.router.add_route("/", simple_handler)
        self.router.add_route("/api/v1/users", complex_handler, Methods.POST)
        self.router.add_route("/files/documents/", lambda: "trailing_slash")
        
        # Validate simple root route
        root_route = self.router.get_route("/", Methods.GET)
        self.assertIsNotNone(root_route)
        self.assertEqual(root_route.handler, simple_handler)
        self.assertEqual(root_route.method, Methods.GET)
        
        # Validate complex nested route with specific method
        api_route = self.router.get_route("/api/v1/users", Methods.POST)
        self.assertIsNotNone(api_route)
        self.assertEqual(api_route.handler, complex_handler)
        self.assertEqual(api_route.method, Methods.POST)
        
        # Validate trailing slash handling
        trailing_route = self.router.get_route("/files/documents/", Methods.GET)
        self.assertIsNotNone(trailing_route)
        
        # Validate path segmentation
        segments = Router.get_segments("/api/v1/users")
        self.assertEqual(segments, ["", "api", "v1", "users"])
        
        # Validate empty and root path segmentation
        self.assertEqual(Router.get_segments("/"), ["", ""])
        self.assertEqual(Router.get_segments("users/profile"), ["users", "profile"])

    def test_add_single_routes_with_multiple_methods(self):
        def get_handler():
            return "get_resource"
        
        def post_handler():
            return "post_resource"
        
        def put_handler():
            return "put_resource"
        
        def patch_handler():
            return "patch_resource"
        
        def delete_handler():
            return "delete_resource"
        
        # Add same path with all HTTP methods
        base_path = "/api/resource"
        method_handlers = {
            Methods.GET: get_handler,
            Methods.POST: post_handler,
            Methods.PUT: put_handler,
            Methods.PATCH: patch_handler,
            Methods.DELETE: delete_handler
        }
        
        for method, handler in method_handlers.items():
            self.router.add_route(base_path, handler, method)
        
        # Verify all methods are accessible and not overriding each other
        for method, expected_handler in method_handlers.items():
            route = self.router.get_route(base_path, method)
            self.assertIsNotNone(route, f"Route not found for method {method}")
            self.assertEqual(route.method, method)
            self.assertEqual(route.handler, expected_handler)
        
        # Test multiple nested paths with shared prefixes
        def users_handler():
            return "users"
        
        def user_profile_handler():
            return "profile"
        
        def user_settings_handler():
            return "settings"
        
        self.router.add_route("/users", users_handler)
        self.router.add_route("/users/profile", user_profile_handler, Methods.POST)
        self.router.add_route("/users/settings", user_settings_handler, Methods.PUT)
        
        # Verify nested routes with different methods
        self.assertEqual(self.router.get_route("/users", Methods.GET).handler, users_handler)
        self.assertEqual(self.router.get_route("/users/profile", Methods.POST).handler, user_profile_handler)
        self.assertEqual(self.router.get_route("/users/settings", Methods.PUT).handler, user_settings_handler)
        
        # Verify cross-method isolation
        self.assertIsNone(self.router.get_route("/users/profile", Methods.GET))
        self.assertIsNone(self.router.get_route("/users/settings", Methods.GET))
