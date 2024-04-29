from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

from datetime import datetime


import sqlalchemy
from src import database as db

""" 
Global Variables
Maintain carts globally temporarily. In future versions this will be done with a cart table.
"""
carts = {}
current_cart_id = 1

def reset_carts():
    carts = {}
    current_cart_id = 1


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
    global current_cart_id
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            f"""
            INSERT INTO carts 
            (id, customer_id)
            VALUES
            ({current_cart_id}, {current_cart_id})"""))
    
    ret = {"cart_id": current_cart_id}
    current_cart_id += 1
    return ret 


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
            INSERT INTO cart_items
            (cart_id, customer_id, item_sku, quantity)
            VALUES
            ({cart_id}, {cart_id}, '{item_sku}', {cart_item.quantity})"""
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
        
        # Get current prices
        result = connection.execute(sqlalchemy.text(
            "SELECT item_sku, price from potion_mixtures")
        )
        for row in result: 
            prices[row[0]] = row[1]
        
        # Update potion_mixtures and calculate gold 
        result = connection.execute(sqlalchemy.text(
            f"""SELECT item_sku, quantity from cart_items
                WHERE cart_id = {cart_id}"""))
        
        for row in result:
            # items_purchased[row[0]] = row[1]
            connection.execute(sqlalchemy.text(
                f"""UPDATE potion_mixtures
                    SET quantity = quantity - :purchased
                    WHERE item_sku = '{row[0]}' """),
                [{"purchased": row[1]}]
            )
            
            gold_paid += prices[row[0]] * row[1]
            total_sold += row[1]
            
        result = connection.execute(sqlalchemy.text(
            f"""DELETE from cart_items
                WHERE cart_id = {cart_id}"""))
        
        result = connection.execute(sqlalchemy.text(
            f"""DELETE from carts
                WHERE id = {cart_id}"""))
        
        # Update gold balance 
        connection.execute(sqlalchemy.text(
            f"""UPDATE global_inventory
                SET gold = gold + :gold_paid"""),
            [{"gold_paid": gold_paid}]
        )
        
    return {"total_potions_bought": total_sold, "total_gold_paid": gold_paid}
