from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

from src.util import get_ml_color_type

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int
    
@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    
    # Key = potion_type_tuple
    # Value = quantity
    update_potion_mixtures = []
    
    for potion_delivery in potions_delivered:
        update_potion_mixtures[tuple(potion_delivery.potion_type)] = potion_delivery.quantity
        
        used_ml_red = potion_delivery.potion_type[0]
        used_ml_green = potion_delivery.potion_type[1]
        used_ml_blue = potion_delivery.potion_type[2]
        used_ml_dark = potion_delivery.potion_type[3]
        
        if used_ml_red > 0:
            update_potion_mixtures.append({"description": f"""Mixed potion of type: 
                {potion_delivery.potion_type}""", 
                "type": {get_ml_color_type(potion_delivery.potion_type)}, 
                "change": -used_ml_red
            })
        if used_ml_green > 0:
            update_potion_mixtures.append({"description": f"""Mixed potion of type: 
                {potion_delivery.potion_type}""", 
                "type": {get_ml_color_type(potion_delivery.potion_type)}, 
                "change": -used_ml_green
            })
        if used_ml_blue > 0:
            update_potion_mixtures.append({"description": f"""Mixed potion of type: 
                {potion_delivery.potion_type}""", 
                "type": {get_ml_color_type(potion_delivery.potion_type)}, 
                "change": -used_ml_blue
            })
        if used_ml_dark > 0:
            update_potion_mixtures.append({"description": f"""Mixed potion of type: 
                {potion_delivery.potion_type}""", 
                "type": {get_ml_color_type(potion_delivery.potion_type)}, 
                "change": -used_ml_dark
            })
                
    with db.engine.begin() as connection:
        # Execute ml_ledger update
        result = connection.execute(
            sqlalchemy.text(
                """INSERT INTO ml_ledger ((description, type, change))
                    VALUES (:description, :type, :change)"""
            ), 
            update_potion_mixtures
        )
        

    
    # Remove final comma from sql_ml_ledger_string
    sql_ml_ledger_string = sql_ml_ledger_string[:-1]
    
    with db.engine.begin() as connection:
        # Execute ml_ledger update
        result = connection.execute(sqlalchemy.text(sql_ml_ledger_string))
        # Update potion ledger
        for potion_type_tuple, quantity in update_potion_mixtures.items():
            result = connection.execute(
                sqlalchemy.text(
                    f"""
                    INSERT INTO potion_ledger (potion_id, description, change)
                    SELECT potion_mixtures.id, 'Mixed potion with type:{potion_type_tuple}', {quantity} 
                    FROM potion_mixtures
                    WHERE potion_mixtures.num_red_ml = {potion_type_tuple[0]} AND
                          potion_mixtures.num_green_ml = {potion_type_tuple[1]} AND
                          potion_mixtures.num_blue_ml = {potion_type_tuple[2]} AND
                          potion_mixtures.num_dark_ml = {potion_type_tuple[3]}
                    """
                )
            )
        
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    bottle_plan = []

    inventory_red_ml = 0
    inventory_green_ml = 0
    inventory_blue_ml = 0
    with db.engine.begin() as connection:
        # Calculate ml inventory
        inventory_red_ml = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0) 
            FROM ml_ledger
            WHERE type = 'RED'
            """
        )).scalar_one()
        
        inventory_green_ml = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0)
            FROM ml_ledger
            WHERE type = 'GREEN'
            """
        )).scalar_one()
        
        inventory_blue_ml = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0)
            FROM ml_ledger
            WHERE type = 'BLUE'
            """
        )).scalar_one()
        
        # Order potion mixtures from lowest quantity to highest quantity
        result = connection.execute(
            sqlalchemy.text("""
                SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml,
                       COALESCE(SUM(potion_ledger.change), 0) AS quantity 
                FROM potion_mixtures 
                LEFT JOIN potion_ledger ON potion_mixtures.id = potion_ledger.potion_id
                GROUP BY num_red_ml, num_green_ml, num_blue_ml, num_dark_ml
                ORDER BY quantity ASC
            """)
        )
        for row in result:
            red_ml = row.num_red_ml
            green_ml = row.num_green_ml
            blue_ml = row.num_blue_ml
            dark_ml = row.num_dark_ml
            quantity = row.quantity

            # Check if we have inventory to mix
            if (inventory_red_ml >= red_ml and 
                inventory_green_ml >= green_ml and
                inventory_blue_ml >= blue_ml):
                
                # Add to plan
                bottle_plan.append(
                    {
                        "potion_type": [red_ml, green_ml, blue_ml, 0],
                        "quantity": 1,
                    }
                )
                # Update local inventory
                inventory_red_ml -= red_ml
                inventory_green_ml -= green_ml
                inventory_blue_ml -= blue_ml
                
    
    print(f"BOTTLE PLAN: {bottle_plan}")
    return bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())