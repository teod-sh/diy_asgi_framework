# diy_asgi_framework

This is a simple ASGI framework that I have built for learning purposes.

If you want to see the articles I have produced based on this code, please visit [my tech blog](https://teod-sh.github.io/)

## ! Warning !
**It is far away from being production-ready.**

But it is a pretty good foundation for building your own ASGI framework. For sure, you will need to invest quite a bit of time in it...

## Features

### 🚀 Core ASGI Application
- **HTTP request handling** - Supports HTTP request with GET, POST, PUT, PATCH, DELETE methods
- **Lifespan management** - Proper application startup and shutdown lifecycle handling

### 🛣️ Advanced Routing System
- **Tree-based router** - Efficient path matching using a tree data structure for optimal performance
- **Multiple HTTP methods per route** - Support for handling multiple HTTP methods on the same endpoint
- **Route grouping** - Organize routes using `ApiRouter` for modular application structure
- **Method validation** - Automatic validation of allowed HTTP methods with proper error responses

### 📡 Request Handling
- **Typed request data** - Generic type support for query parameters and request body
- **Streaming request body** - Efficient handling of large request bodies with async generators
- **JSON body parsing** - Built-in JSON parsing with error handling
- **Query String parsing** - Built-in Query String parsing with support for multiple values and type conversion
- **Header access** - Easy access to request headers with built-in parsing and manipulation
- **Custom extractors** - Configurable query string and body extractors for data transformation
- **Request validation** - Built-in request validation with custom exception handling

### 📤 Response System
- **Two response types** - Support for JSON and Text responses
- **HTTP status codes** - Comprehensive set of standard HTTP status codes
- **Custom headers** - Easy header management and manipulation
- **Response encoding** - Configurable character encoding (default UTF-8)
- **Pre-built response helpers** - Convenient response creators for common scenarios (404, 400, 500, etc.)

### ⚙️ Background Task Processing
- **Async task queue** - Built-in background task processing system
- **Task retry mechanism** - Configurable retry logic with maximum attempt limits
- **Task timeouts** - Configurable timeouts to prevent stuck tasks
- **Concurrent task execution** - Configurable maximum concurrent tasks
- **Graceful shutdown** - Proper cleanup of background tasks during application shutdown
- **Task parameters** - Type-safe task parameter passing

### 🛡️ Error Handling
- **Custom exceptions** - Structured exception hierarchy for different error types
- **Automatic error responses** - Built-in HTTP error response generation
- **Request validation errors** - Proper handling of malformed requests
- **Method not allowed handling** - Automatic 405 responses for unsupported methods

### 🔧 Middleware System
- **Global middleware** - Apply middleware functions to all routes for cross-cutting concerns
- **Middleware chaining** - Support for multiple middleware functions executed in order
- **Async middleware support** - Full async/await support for non-blocking middleware operations


## Usage example can be found in `sample.py` file
```bash
pip install uvicorn
uvicorn sample:app
```