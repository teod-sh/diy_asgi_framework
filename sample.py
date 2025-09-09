from asgi.app import App
from asgi.api_router import ApiRouter
from asgi.request_data import RequestData
from asgi.types import Methods

router1_pkg_sample_1 = ApiRouter()

@router1_pkg_sample_1.get("/home")
async def home(request_data):
    print("home triggered")


router2_pkg_sample_2 = ApiRouter()
@router2_pkg_sample_2.get("/about")
async def about(request_data):
    print("about triggered")


def qs_extractor(qs: dict) -> dict:
    return qs

def body_extractor(body: bytes) -> int:
    return 1

@router2_pkg_sample_2.multi_methods(
    "/about/careers",
    [Methods.GET, Methods.POST],
    qs_extractor,
    body_extractor
)
async def about(request_data: RequestData[dict, int]):
    print("about careers triggered")
    qs = await request_data.get_query_string_params()
    body = await request_data.get_body()
    print(qs, body)


app = App()
app.include_routes([router1_pkg_sample_1, router2_pkg_sample_2])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)