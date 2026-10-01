
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastmcp import Client
import time
from collections import defaultdict


from logger import get_logger

logger = get_logger("api")

app = FastAPI(title="Shopping Cart API")

MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"

# ---------- Metrics (memory me, restart pe reset hote hain) ----------
START_TIME = time.time()
metrics = {
    "total_requests": 0,
    "errors": 0,
    "by_endpoint": defaultdict(int),
    "mcp_calls": defaultdict(int),
}


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1


# ---------- Logging + metrics middleware ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    metrics["total_requests"] += 1
    metrics["by_endpoint"][f"{request.method} {request.url.path}"] += 1
    if response.status_code >= 400:
        metrics["errors"] += 1

    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f} ms)"
    )
    return response


# ---------- MCP server ko call karne ka helper ----------
async def call_mcp(tool_name: str, args: dict | None = None):
    logger.info(f"Calling MCP tool: {tool_name} | args={args}")
    metrics["mcp_calls"][tool_name] += 1
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(tool_name, args or {})
            return result.data
    except Exception as e:
        logger.error(f"MCP call failed for {tool_name}: {e}")
        raise HTTPException(status_code=503, detail="MCP server se connect nahi ho paya")


# ---------- Endpoints ----------
@app.get("/products")
async def get_products():
    return await call_mcp("list_products")


@app.post("/cart/add")
async def add_to_cart(body: AddToCartRequest):
    return await call_mcp(
        "add_to_cart", {"product_id": body.product_id, "quantity": body.quantity}
    )


@app.delete("/cart/remove/{product_id}")
async def remove_from_cart(product_id: int):
    return await call_mcp("remove_from_cart", {"product_id": product_id})


@app.get("/cart")
async def get_cart():
    return await call_mcp("view_cart")


@app.post("/checkout")
async def checkout():
    return await call_mcp("checkout")


@app.get("/orders")
async def get_orders():
    return await call_mcp("get_orders")


@app.get("/health")
async def health():
    try:
        async with Client(MCP_SERVER_URL) as client:
            await client.ping()
        return {"api": "ok", "mcp_server": "ok"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"api": "ok", "mcp_server": "down"}


@app.get("/metrics")
async def get_metrics():
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": metrics["total_requests"],
        "errors": metrics["errors"],
        "requests_by_endpoint": dict(metrics["by_endpoint"]),
        "mcp_tool_calls": dict(metrics["mcp_calls"]),
    }


# ---------- Frontend ----------
@app.get("/")
async def home():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")