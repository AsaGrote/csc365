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
    red_potions_mixed = 0
    green_potions_mixed = 0
    blue_potions_mixed = 0
    for potion_delivery in potions_delivered:
        if potion_delivery.potion_type == [100, 0, 0, 0]:
            used_ml_red += 100*potion_delivery.quantity
            red_potions_mixed += potion_delivery.quantity
        elif potion_delivery.potion_type == [0, 100, 0, 0]:
            used_ml_green += 100*potion_delivery.quantity
            green_potions_mixed += potion_delivery.quantity
        elif potion_delivery.potion_type == [0, 0, 100, 0]:
            used_ml_blue += 100*potion_delivery.quantity
            blue_potions_mixed += potion_delivery.quantity
    
    if green_potions_mixed > 0:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("""SELECT num_red_potions, 
                    num_green_potions, num_blue_potions, num_red_ml, num_green_ml, 
                    num_blue_ml, from global_inventory"""))
            row = result.one()
            initial_num_red_potions = row[0]
            initial_num_green_potions = row[1]
            initial_num_blue_potions = row[2]
            initial_red_ml = row[3]
            initial_green_ml = row[4]
            initial_blue_ml = row[5]
            result = connection.execute(sqlalchemy.text(f"""UPDATE global_inventory 
                    SET num_red_potions = {initial_num_red_potions+red_potions_mixed}, 
                        num_green_potions = {initial_num_green_potions+green_potions_mixed}, 
                        num_blue_potions = {initial_num_blue_potions+blue_potions_mixed}, 
                        num_red_ml = {initial_red_ml-used_ml_red},
                        num_green_ml = {initial_green_ml-used_ml_green},
                        num_blue_ml = {initial_blue_ml-used_ml_blue}"""))
    
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into green potions.

    red_ml = 0
    green_ml = 0
    blue_ml = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml from global_inventory"))
        row = result.one()
        red_ml = row[0]
        green_ml = row[1]
        blue_ml = row[2]
        
    num_red_potions = red_ml // 100
    num_green_potions = green_ml // 100
    num_blue_potions = blue_ml // 100
    
    bottle_plan = []
    
    if num_red_potions > 0:
        bottle_plan.append(
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": num_red_potions,
            }
        )
    if num_green_potions > 0:
        bottle_plan.append(
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": num_green_potions,
            }
        )
    if num_blue_potions > 0:
        bottle_plan.append(
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": num_blue_potions,
            }
        )
    
    return bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())