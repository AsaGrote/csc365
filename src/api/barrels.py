from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

from src.util import get_ml_color_type

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
    gold_spent = 0
    sql_ml_ledger_string = "INSERT into ml_ledger (description, type, change) VALUES "
    for idx, barrel  in enumerate(barrels_delivered):
        if barrel.sku == "SMALL_RED_BARREL":
            gold_spent += barrel.price*barrel.quantity
        elif barrel.sku == "SMALL_GREEN_BARREL":
            gold_spent += barrel.price*barrel.quantity
        elif barrel.sku == "SMALL_BLUE_BARREL":
            gold_spent += barrel.price*barrel.quantity
            
        sql_ml_ledger_string += f""" ('Barrel order {order_id} delivered.
            {barrel.sku} purchased.', '{get_ml_color_type(barrel.potion_type)}',
            {barrel.ml_per_barrel * barrel.quantity}),"""
    
    # Remove final comma from sql_ml_ledger_string
    sql_ml_ledger_string = sql_ml_ledger_string[:-1]
            
    # Update database
    if gold_spent > 0:
        with db.engine.begin() as connection: 
            # Execute ml_ledger update
            result = connection.execute(sqlalchemy.text(sql_ml_ledger_string)) 
                      
            # Update gold ledger
            result = connection.execute(sqlalchemy.text(
                f"""
                INSERT into gold_ledger (description, change)
                VALUES ('Barrel order {order_id} delivered', {-gold_spent})
                """
            ))
    
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
    
    # Calculate ml inventory
    num_ml_red = 0
    num_ml_green = 0
    num_ml_blue = 0
    gold = 0
    with db.engine.begin() as connection:
        num_ml_red = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0) 
            FROM ml_ledger
            WHERE type = 'RED'
            """
        )).scalar_one()
        
        num_ml_green = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0)
            FROM ml_ledger
            WHERE type = 'GREEN'
            """
        )).scalar_one()
        
        num_ml_blue = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0)
            FROM ml_ledger
            WHERE type = 'BLUE'
            """
        )).scalar_one()
        
        
        result = connection.execute(sqlalchemy.text("SELECT SUM(change) from gold_ledger"))
        gold = result.scalar_one()
        
        # add potion inventory to ml calculation
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, quantity from potion_mixtures"))
        result = connection.execute(sqlalchemy.text(
            """SELECT SUM(change) AS quantity, potion_mixtures.num_red_ml, 
                    potion_mixtures.num_green_ml, potion_mixtures.num_blue_ml 
               FROM potion_ledger
               LEFT JOIN potion_mixtures ON potion_mixtures.id = potion_ledger.potion_id
               GROUP BY potion_mixtures.num_red_ml, 
                        potion_mixtures.num_green_ml, 
                        potion_mixtures.num_blue_ml"""
        ))
        for row in result:
            num_ml_red += row[1] * row[0]
            num_ml_green += row[2] * row[0]
            num_ml_blue += row[3] * row[0]
    
    
    # Buy as much as possible, prioritizing smallest value of ml first
    purchase_plan = []
    
    ml_inventory = [
        ("num_ml_red", num_ml_red), 
        ("num_ml_green", num_ml_green),
        ("num_ml_blue", num_ml_blue)
    ]
    
    order = sorted(ml_inventory, key=lambda potion: potion[1])
    
    for i in range(len(order)):
        if order[i][0] == "num_ml_red":
            if red_barrel_obj and gold >= red_barrel_obj.price:
                purchase_plan.append(
                    {
                        "sku": "SMALL_RED_BARREL",
                        "quantity": 1
                    }
                )
                gold -= red_barrel_obj.price
        elif order[i][0] == "num_ml_green":
            if green_barrel_obj and gold >= green_barrel_obj.price:
                purchase_plan.append(
                    {
                        "sku": "SMALL_GREEN_BARREL",
                        "quantity": 1
                    }
                )
                gold -= green_barrel_obj.price
        elif order[i][0] == "num_ml_blue":
            if blue_barrel_obj and gold >= blue_barrel_obj.price:
                purchase_plan.append(
                    {
                        "sku": "SMALL_BLUE_BARREL",
                        "quantity": 1
                    }
                )
                gold -= blue_barrel_obj.price
    
    print(f"PURCHASE PLAN: {purchase_plan}")
    
    return purchase_plan
