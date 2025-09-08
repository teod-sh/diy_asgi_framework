from router import Router


async def home():
    print("home triggered")

async def users():
    print("users triggered")

class App:

    def __init__(self):
        self.router = Router()
        self.router.add_route("/", home)
        self.router.add_route("/users", users)

    async def __call__(self, scope, receive, send):
        target = self.router.get_route(scope['path'])

        # following the specs, in order to provide a response to our caller/client
        # we must follow the two steps you see below
        # !keep a closer eye to the type of each send call
        # with http.response.start we can provide status code, headers [considering we are dealing with http requests]
        # with the http.response.body we can provide a flag finalizing if we are planning to send more data [streaming like] and the payload/chunk
        # this is enough for now, we will get back to it after to improve and add more details and fix a few things

        if target is None:
            print("handler not found, ignoring")
            await send({"type": "http.response.start", "status": 404})
            await send({"type": "http.response.body", "body": b"not found"})
            return

        print("handler found")
        await target.handler()
        await send({"type": "http.response.start", "status": 200})
        await send({"type": "http.response.body", "body": b"ok"})


app = App()


# await send({
#     'type': 'http.response.start',
#     'status': 200,  # HTTP status code
#     'headers': [    # List of 2-tuples (name, value) - both as bytes
#         (b'content-type', b'application/json'),
#         (b'content-length', b'42'),
#         (b'custom-header', b'custom-value')
#     ]
# })