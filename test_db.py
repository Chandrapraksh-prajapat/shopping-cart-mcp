from db import run_query

products = run_query("SELECT * FROM products", fetch=True)
for p in products:
    print(p)