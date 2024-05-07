from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

from datetime import datetime


import sqlalchemy
from sqlalchemy import func
from src import database as db


router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    
    results = []
    
    # Use reflection to derive table schema.
    metadata_obj = sqlalchemy.MetaData()
    customer = sqlalchemy.Table("customer", metadata_obj, autoload_with=db.engine)
    orders = sqlalchemy.Table("orders", metadata_obj, autoload_with=db.engine)
    
    if sort_col is search_sort_options.customer_name:
        order_by = customer.c.customer_name
    elif sort_col is search_sort_options.item_sku:
        order_by = orders.c.item_desc
    elif sort_col is search_sort_options.line_item_total:
        order_by = orders.c.gold
    elif sort_col is search_sort_options.timestamp:
        order_by = orders.c.created_at
    else:
        assert False
        
    # Check if descending
    if sort_order is search_sort_order.desc:
        order_by = sqlalchemy.desc(order_by)
        
    offset = 0 if search_page == "" else int(search_page)*5
    stmt = (
        sqlalchemy.select(
            orders.c.id,
            customer.c.customer_name,
            orders.c.item_desc,
            orders.c.gold,
            orders.c.created_at,
        )
        .join(customer, customer.c.id == orders.c.customer_id)
        .limit(6)
        .offset(offset)
        .order_by(order_by, orders.c.created_at)
    )
    
    # filter by customer name if param is passed
    if customer_name != "":
        stmt = stmt.where(customer.c.customer_name.ilike(f"%{customer_name}%"))
    
    # filter by potion_sku if param is passed
    if potion_sku != "":
        stmt = stmt.where(orders.c.item_desc.ilike(f"%{potion_sku}%"))
    
    num_results_remaining = 0
    with db.engine.begin() as connection:
        result = connection.execute(stmt)
        
        for row in result:
            results.append({
                "line_item_id": row.id,
                "item_sku": row.item_desc,
                "customer_name": row.customer_name,
                "line_item_total": row.gold,
                "timestamp": row.created_at,
            })

    # There are additional results if there is at least 1 additional result 
    # after returning 5 results (1+5=6 total)
    results_remaining = True if len(results) == 6 else False
    
    return {
        "previous": "" if search_page in ["0", ""] else f"{int(search_page)-1}",
        "next": "" if not results_remaining else ("1" if search_page == "" else f"{int(search_page)+1}"),
        "results": results[:5], #Return only 5 results per page
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO customer (customer_name, character_class, level)
            VALUES ('{new_cart.customer_name}', '{new_cart.character_class}', '{new_cart.level}')
            RETURNING id"""))
        
        customer_id = result.scalar_one()
        
        result = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO carts (customer_id)
            VALUES ('{customer_id}')
            RETURNING id"""))
        
        cart_id = result.scalar_one()
        
    
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    
    """ 
    TODO: Remove things from catalog when they are added to the cart to avoid anomalies
    """
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO cart_items (potion_id, cart_id, quantity)
            SELECT potion_mixtures.id, {cart_id}, {cart_item.quantity}
            FROM potion_mixtures
            WHERE potion_mixtures.item_sku = '{item_sku}' """
        ))
    
    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    
    """ TODO: Audit checkouts to avoid anomalies """
    
    print(f"cartCheckout.payment={cart_checkout.payment}")
    
    gold_paid = 0
    total_sold = 0 
    
    with db.engine.begin() as connection:
        # Update orders table
        result = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO orders (customer_id, item_desc, gold)
            SELECT
                carts.customer_id AS customer_id,
                CONCAT(quantity, ' ', potion_mixtures.name, ' ', 'potion(s)') AS item_desc,
                cart_items.quantity*potion_mixtures.price AS gold
            FROM cart_items
                JOIN potion_mixtures ON potion_mixtures.id = cart_items.potion_id
                JOIN carts ON carts.id = cart_items.cart_id
            WHERE cart_items.cart_id = {cart_id}
            """)
        )
        
        # Update potion_ledger
        result = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO potion_ledger (potion_id, change, description) 
            SELECT potion_id, quantity*-1 AS change, 'Checkout cart {cart_id}'
            FROM cart_items WHERE cart_items.cart_id = {cart_id}
            """)
        )
        
        # Update gold_ledger
        result = connection.execute(sqlalchemy.text(
            f"""
            SELECT cart_items.quantity, potion_mixtures.price FROM potion_mixtures
            LEFT JOIN cart_items ON cart_items.potion_id = potion_mixtures.id
            WHERE cart_items.cart_id = {cart_id}
            """)
        )
        for quantity, price in result:
            gold_paid += quantity*price
            total_sold += quantity

        result = connection.execute(sqlalchemy.text(
            f"""INSERT INTO gold_ledger (description, change) 
                VALUES ('Checkout cart {cart_id}', {gold_paid})"""
        ))
        
        # Clean up cart_items
        result = connection.execute(sqlalchemy.text(
            f"""DELETE from cart_items
                WHERE cart_id = {cart_id}"""))
        
        # Clean up carts
        result = connection.execute(sqlalchemy.text(
            f"""DELETE from carts
                WHERE id = {cart_id}"""))
        
    return {"total_potions_bought": total_sold, "total_gold_paid": gold_paid}
