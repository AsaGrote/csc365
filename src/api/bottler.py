from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

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
    
    used_ml_red = 0
    used_ml_green = 0
    used_ml_blue = 0
    used_ml_dark = 0
    
    # Key = potion_type_tuple
    # Value = id
    local_potion_mixtures = {}
    
    # Get initial inventory and current potion mixtures
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml from global_inventory"""
            ))
        row = result.one()
        initial_red_ml = row[0]
        initial_green_ml = row[1]
        initial_blue_ml = row[2]
        initial_dark_ml = row[3]
        
        result = connection.execute(
            sqlalchemy.text(
                """SELECT id, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, quantity from potion_mixtures"""
            ))
        for row in result:
            local_potion_mixtures[(row[1], row[2], row[3], row[4])] = row[0]
            
    # Key = potion_type_tuple
    # Value = quantity
    update_potion_mixtures = {}
    
    for potion_delivery in potions_delivered:
        if tuple(potion_delivery.potion_type) in local_potion_mixtures:
            update_potion_mixtures[tuple(potion_delivery.potion_type)] = potion_delivery.quantity
            
            used_ml_red += potion_delivery.potion_type[0]
            used_ml_green += potion_delivery.potion_type[1]
            used_ml_blue += potion_delivery.potion_type[2]
            used_ml_dark += potion_delivery.potion_type[3]
        
    # Update ml and potion inventory
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(f"""UPDATE global_inventory 
                SET num_red_ml = num_red_ml - :used_ml_red,
                    num_green_ml = num_green_ml - :used_ml_green,
                    num_blue_ml = num_blue_ml - :used_ml_blue"""),
            [{"used_ml_red": used_ml_red, "used_ml_green": used_ml_green, "used_ml_blue": used_ml_blue}]
        )
        
        for potion_type_tuple, quantity in update_potion_mixtures.items():
            result = connection.execute(
                sqlalchemy.text(f"""UPDATE potion_mixtures 
                    SET quantity = quantity + :added_quantity
                    WHERE id = :id"""),
                [{"added_quantity": quantity, "id": local_potion_mixtures[potion_type_tuple]}]
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
        inventory_result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml from global_inventory"))
        row = inventory_result.one()
        inventory_red_ml = row[0]
        inventory_green_ml = row[1]
        inventory_blue_ml = row[2]
        
        potion_mixture_result = connection.execute(
            sqlalchemy.text("""SELECT num_red_ml, num_green_ml, num_blue_ml, 
                    quantity from potion_mixtures ORDER BY quantity ASC"""))
        for row in potion_mixture_result:
            print(row)
            red_ml = row[0]
            green_ml = row[1]
            blue_ml = row[2]
            quantity = row[3]

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