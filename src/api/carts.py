from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

from datetime import datetime


import sqlalchemy
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

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
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
    
    # items_purchased = {}
    prices = {}
    
    with db.engine.begin() as connection:
        
        result = connection.execute(sqlalchemy.text(
            """
            UPDATE potion_mixtures
            SET quantity = potion_mixtures.quantity - cart_items.quantity
            FROM cart_items
            WHERE potion_mixtures.id = cart_items.potion_id
            RETURNING cart_items.quantity, potion_mixtures.price
            """)
        )
        
        for quantity, price in result:
            gold_paid += quantity*price
            total_sold += quantity

        result = connection.execute(sqlalchemy.text(
            """
            UPDATE global_inventory
            SET gold = global_inventory.gold - :gold_paid
            """),
            [{"gold_paid": gold_paid}]
        ) 
        
        result = connection.execute(sqlalchemy.text(
            f"""DELETE from cart_items
                WHERE cart_id = {cart_id}"""))
        
        result = connection.execute(sqlalchemy.text(
            f"""DELETE from carts
                WHERE id = {cart_id}"""))
        
    return {"total_potions_bought": total_sold, "total_gold_paid": gold_paid}
