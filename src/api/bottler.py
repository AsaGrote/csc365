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
    
    used_ml_green = 0
    green_potions_mixed = 0
    for potion_delivery in potions_delivered:
        if potion_delivery.potion_type == [0, 100, 0, 0]:
            used_ml_green += 100*potion_delivery.quantity
            green_potions_mixed += potion_delivery.quantity
        else:
            print("Error: not a green potion.")
    
    if green_potions_mixed > 0:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("SELECT * from global_inventory"))
            row = result.one()
            initial_num_green_potions = row[0]
            initial_green_ml = row[1]
            result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_potions = {initial_num_green_potions+green_potions_mixed}, num_green_ml = {initial_green_ml-used_ml_green}"))
    
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    green_ml = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * from global_inventory"))
        green_ml = result.one()[1]
        
    num_green_potions = green_ml // 100
    
    if num_green_potions > 0:
        return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": num_green_potions,
            }
        ]
    else:
        return []

if __name__ == "__main__":
    print(get_bottle_plan())