
from fastmcp import FastMCP
from db import run_query, get_db_connection
from logger import get_logger
from decimal import Decimal


logger = get_logger("cart_server")

mcp = FastMCP("Shopping Cart Server")

USER_ID = 1  # abhi ek hi user maan ke chal rahe hain


@mcp.tool
def list_products() -> dict:
    """Saare available products ki list return karta hai."""
    logger.info("Tool called: list_products")
    rows = run_query("SELECT id, name, price, stock FROM products", fetch=True)
    for r in rows:
        r["price"] = float(r["price"])
    return {"products": rows}


@mcp.tool
def add_to_cart(product_id: int, quantity: int = 1) -> dict:
    """Product ko cart me add karta hai (stock check ke saath)."""
    logger.info(f"Tool called: add_to_cart(product_id={product_id}, quantity={quantity})")

    if quantity <= 0:
        return {"success": False, "message": "Quantity 1 ya usse zyada honi chahiye"}

    product = run_query(
        "SELECT id, name, stock FROM products WHERE id = %s",
        (product_id,),
        fetch=True,
    )
    if not product:
        logger.warning(f"Product {product_id} not found")
        return {"success": False, "message": f"Product {product_id} not found"}

    if quantity > product[0]["stock"]:
        return {"success": False, "message": f"Sirf {product[0]['stock']} stock available hai"}

    run_query(
        """INSERT INTO cart_items (user_id, product_id, quantity)
           VALUES (%s, %s, %s)
           ON DUPLICATE KEY UPDATE quantity = quantity + %s""",
        (USER_ID, product_id, quantity, quantity),
    )
    return {"success": True, "message": f"{product[0]['name']} cart me add ho gaya"}


@mcp.tool
def remove_from_cart(product_id: int) -> dict:
    """Product ko cart se hata deta hai."""
    logger.info(f"Tool called: remove_from_cart(product_id={product_id})")
    affected = run_query(
        "DELETE FROM cart_items WHERE user_id = %s AND product_id = %s",
        (USER_ID, product_id),
    )
    if affected == 0:
        return {"success": False, "message": "Ye product cart me nahi hai"}
    return {"success": True, "message": "Product cart se hata diya"}


@mcp.tool
def view_cart() -> dict:
    """Cart ke saare items aur total price return karta hai."""
    logger.info("Tool called: view_cart")
    rows = run_query(
        """SELECT p.id AS product_id, p.name, p.price, c.quantity
           FROM cart_items c
           JOIN products p ON p.id = c.product_id
           WHERE c.user_id = %s""",
        (USER_ID,),
        fetch=True,
    )
    total = 0.0
    for r in rows:
        r["price"] = float(r["price"])
        r["subtotal"] = r["price"] * r["quantity"]
        total += r["subtotal"]
    return {"items": rows, "total": total}


@mcp.tool
def checkout() -> dict:
    """Cart ke items ka order place karta hai, stock kam karta hai aur cart khali kar deta hai."""
    logger.info("Tool called: checkout")

    # Checkout me kai queries ek saath honi chahiye (sab ho ya koi nahi),
    # isliye yahan ek hi connection aur ek transaction use karte hain.
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT c.product_id, c.quantity, p.name, p.price, p.stock
               FROM cart_items c
               JOIN products p ON p.id = c.product_id
               WHERE c.user_id = %s
               FOR UPDATE""",
            (USER_ID,),
        )
        items = cursor.fetchall()

        if not items:
            return {"success": False, "message": "Cart khali hai"}

        # Stock check
        for it in items:
            if it["quantity"] > it["stock"]:
                return {
                    "success": False,
                    "message": f"{it['name']} ka sirf {it['stock']} stock bacha hai",
                }

        total = sum(Decimal(it["price"]) * it["quantity"] for it in items)

        cursor.execute(
            "INSERT INTO orders (user_id, total) VALUES (%s, %s)", (USER_ID, total)
        )
        order_id = cursor.lastrowid

        for it in items:
            cursor.execute(
                """INSERT INTO order_items (order_id, product_id, quantity, price)
                   VALUES (%s, %s, %s, %s)""",
                (order_id, it["product_id"], it["quantity"], it["price"]),
            )
            cursor.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (it["quantity"], it["product_id"]),
            )

        cursor.execute("DELETE FROM cart_items WHERE user_id = %s", (USER_ID,))
        conn.commit()

        logger.info(f"Checkout done: order_id={order_id}, total={total}")
        return {
            "success": True,
            "message": "Order place ho gaya",
            "order_id": order_id,
            "total": float(total),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Checkout failed: {e}")
        return {"success": False, "message": "Checkout fail ho gaya"}
    finally:
        cursor.close()
        conn.close()


@mcp.tool
def get_orders() -> dict:
    """Purane saare orders ki list return karta hai."""
    logger.info("Tool called: get_orders")
    rows = run_query(
        """SELECT o.id AS order_id, o.total, o.created_at,
                  COUNT(oi.id) AS items_count
           FROM orders o
           LEFT JOIN order_items oi ON oi.order_id = o.id
           WHERE o.user_id = %s
           GROUP BY o.id, o.total, o.created_at
           ORDER BY o.id DESC""",
        (USER_ID,),
        fetch=True,
    )
    for r in rows:
        r["total"] = float(r["total"])
        r["created_at"] = str(r["created_at"])
    return {"orders": rows}


if __name__ == "__main__":
    logger.info("Starting Shopping Cart MCP Server on port 8001")
    mcp.run(transport="http", host="0.0.0.0", port=8001)