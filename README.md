# Shopping Cart (FastAPI + MCP Server + MySQL)

A single-page shopping cart application. The frontend talks to FastAPI, FastAPI calls tools on an MCP server, and the MCP server reads and writes data in MySQL.

```
Frontend (index.html) -> FastAPI (main.py) -> MCP Server (cart_server.py) -> MySQL
```

## Features

- Product listing with stock information
- Add to cart, remove from cart, and total price calculation
- Checkout: creates an order, reduces stock, and clears the cart (done in a single database transaction)
- Past orders history
- Logging to both the console and the `logs/` folder
- Monitoring: `/health` endpoint, `/metrics` endpoint, and a request-timing middleware

## Tech Stack

- **Backend API:** FastAPI + Uvicorn
- **MCP Server:** FastMCP
- **Database:** MySQL (`mysql-connector-python`)
- **Frontend:** Plain HTML, CSS, and JavaScript (single page)

## Project Structure

```
shopping_cart/
├── mcp_server/
│   ├── __init__.py
│   └── cart_server.py      # MCP tools
├── static/
│   └── index.html          # Single-page frontend
├── logs/                   # Auto-created log files
├── main.py                 # FastAPI app (MCP client)
├── db.py                   # MySQL connection and query helper
├── logger.py               # Logging configuration
├── schema.sql              # Database schema and sample data
├── requirements.txt
├── .env                    # Database credentials (not committed)
└── .gitignore
```

## Prerequisites

- Python 3.10 or higher
- MySQL Server installed and running
- (Optional) MySQL Workbench for running SQL scripts

## Setup

1. **Create and activate a virtual environment**

```powershell
   python -m venv venv
   venv\Scripts\activate
```

2. **Install dependencies**

```powershell
   pip install -r requirements.txt
```

3. **Create the database**

   Run `schema.sql` in MySQL Workbench or from the terminal:

```powershell
   mysql -u root -p < schema.sql
```

   This creates the `products`, `cart_items`, `orders`, and `order_items` tables and inserts sample products.

4. **Configure environment variables**

   Create a `.env` file in the project root:

```
   HOST=localhost
   USER=root
   PASSWORD=your_password
   Database=shopping_cart
```

## Running the Application

Two processes need to run at the same time, so use two terminals (activate the virtual environment in both).

**Terminal 1: MCP server** (run from the project root)

```powershell
python -m mcp_server.cart_server
```

**Terminal 2: FastAPI**

```powershell
uvicorn main:app --reload --port 8000
```

Then open: http://127.0.0.1:8000

Swagger UI is available at: http://127.0.0.1:8000/docs

> Note: If you change `cart_server.py`, restart the MCP server manually (`Ctrl + C`, then run it again). Uvicorn reloads automatically for `main.py`.

## API Endpoints

| Method | Path                      | Description                       |
|--------|---------------------------|-----------------------------------|
| GET    | `/products`               | List all products                 |
| POST   | `/cart/add`               | Add a product to the cart         |
| DELETE | `/cart/remove/{product_id}` | Remove a product from the cart  |
| GET    | `/cart`                   | View cart items and total         |
| POST   | `/checkout`               | Place an order                    |
| GET    | `/orders`                 | List past orders                  |
| GET    | `/health`                 | API and MCP server status         |
| GET    | `/metrics`                | Request and tool-call counters    |
| GET    | `/docs`                   | Swagger UI                        |

Example request body for `POST /cart/add`:

```json
{
  "product_id": 2,
  "quantity": 1
}
```

## MCP Tools

| Tool               | Description                                                        |
|--------------------|--------------------------------------------------------------------|
| `list_products`    | Returns all products with price and stock                          |
| `add_to_cart`      | Adds a product to the cart (validates quantity and stock)          |
| `remove_from_cart` | Removes a product from the cart                                    |
| `view_cart`        | Returns cart items, subtotals, and the total                       |
| `checkout`         | Creates an order, reduces stock, and clears the cart (transaction) |
| `get_orders`       | Returns past orders                                                |

## Logging and Monitoring

**Logging**
- Every API request is logged with method, path, status code, and response time.
- Every MCP tool call is logged on both sides: `Calling MCP tool: ...` (FastAPI) and `Tool called: ...` (MCP server).
- Database queries and errors are logged by `db.py`.
- Logs are written to the console and saved as timestamped files in `logs/`.

**Monitoring**
- `GET /health` reports whether the API and the MCP server are up. The frontend polls it every 10 seconds and shows a green or red status indicator.
- `GET /metrics` returns uptime, total requests, error count, requests per endpoint, and MCP tool calls per tool.

Example `/metrics` response:

```json
{
  "uptime_seconds": 120.4,
  "total_requests": 15,
  "errors": 0,
  "requests_by_endpoint": {"GET /products": 2, "POST /cart/add": 3},
  "mcp_tool_calls": {"list_products": 2, "add_to_cart": 3, "view_cart": 5}
}
```

Metrics are stored in memory and reset when the server restarts. For production use, a tool such as Prometheus with Grafana would be a better fit.

