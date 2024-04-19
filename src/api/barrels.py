from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}") 
    
    # Get transaction info from barrels_delivered
    additional_ml_red = 0
    additional_ml_green = 0
    additional_ml_blue = 0
    gold_spent = 0
    for barrel in barrels_delivered:
        if barrel.sku == "SMALL_RED_BARREL":
            additional_ml_red += barrel.ml_per_barrel*barrel.quantity
            gold_spent += barrel.price*barrel.quantity
        elif barrel.sku == "SMALL_GREEN_BARREL":
            additional_ml_green += barrel.ml_per_barrel*barrel.quantity
            gold_spent += barrel.price*barrel.quantity
        elif barrel.sku == "SMALL_BLUE_BARREL":
            additional_ml_blue += barrel.ml_per_barrel*barrel.quantity
            gold_spent += barrel.price*barrel.quantity
            
    # Update database
    if gold_spent > 0:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, gold from global_inventory"))
            row = result.one()
            initial_red_ml = row[0]
            initial_green_ml = row[1]
            initial_blue_ml = row[2]
            initial_gold = row[3]
            result = connection.execute(sqlalchemy.text(f"""
                    UPDATE global_inventory 
                    SET num_red_ml = {initial_red_ml+additional_ml_red}, 
                        num_green_ml = {initial_green_ml+additional_ml_green}, 
                        num_blue_ml = {initial_blue_ml+additional_ml_blue}, 
                        gold = {initial_gold-gold_spent}"""))
    
    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    
    # Check if small red/green/blue barrels are offered
    red_barrel_obj = None
    green_barrel_obj = None
    blue_barrel_obj = None
    for barrel in wholesale_catalog:
        if barrel.sku == "SMALL_RED_BARREL":
            red_barrel_obj = barrel
        elif barrel.sku == "SMALL_GREEN_BARREL":
            green_barrel_obj = barrel
        elif barrel.sku == "SMALL_BLUE_BARREL":
            blue_barrel_obj = barrel
    
    # Check if green potion stock is low
    quantity_red_potion = 0
    quantity_green_potion = 0
    quantity_blue_potion = 0
    gold = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_green_potions, num_blue_potions, gold from global_inventory"))
        row = result.one()
        quantity_red_potion = row[0]
        quantity_green_potion = row[1]
        quantity_blue_potion = row[2]
        gold = row[3]
        
    # Buy as much as possible, prioritizing smallest value of potions first
    purchase_plan = []
    
    potion_inventory = [
        ("num_red_potion", quantity_red_potion), 
        ("num_green_potion", quantity_green_potion),
        ("num_blue_potion", quantity_blue_potion)
    ]
    
    order = sorted(potion_inventory, key=lambda potion: potion[1])
    
    for i in range(len(order)):
        if order[i][0] == "num_red_potion":
            if red_barrel_obj and quantity_red_potion < 10 and gold >= red_barrel_obj.price:
                purchase_plan.append(
                    {
                        "sku": "SMALL_RED_BARREL",
                        "quantity": 1
                    }
                )
                gold -= red_barrel_obj.price
        elif order[i][0] == "num_green_potion":
            if green_barrel_obj and quantity_green_potion < 10 and gold >= green_barrel_obj.price:
                purchase_plan.append(
                    {
                        "sku": "SMALL_GREEN_BARREL",
                        "quantity": 1
                    }
                )
                gold -= green_barrel_obj.price
        elif order[i][0] == "num_blue_potion":
            if blue_barrel_obj and quantity_blue_potion < 10 and gold >= blue_barrel_obj.price:
                purchase_plan.append(
                    {
                        "sku": "SMALL_BLUE_BARREL",
                        "quantity": 1
                    }
                )
                gold -= blue_barrel_obj.price
    
    print(f"PURCHASE PLAN: {purchase_plan}")
    
    return purchase_plan
