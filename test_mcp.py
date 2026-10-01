import asyncio
from fastmcp import Client


async def main():
    async with Client("http://127.0.0.1:8001/mcp") as client:
        print("Products:", (await client.call_tool("list_products", {})).data)
        print("Add:", (await client.call_tool("add_to_cart", {"product_id": 1, "quantity": 2})).data)
        print("Cart:", (await client.call_tool("view_cart", {})).data)


asyncio.run(main())