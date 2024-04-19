from fastapi import APIRouter

import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    
    # Get quantity green potions
    num_red_potions = 0
    num_green_potions = 0
    num_blue_potions = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions, num_green_potions, num_blue_potions from global_inventory"))
        row = result.one()
        num_red_potions = row[0]
        num_green_potions = row[1]
        num_blue_potions = row[2]

    catalog = []

    if num_red_potions > 0:
        catalog.append(
            {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": num_red_potions,
                "price": 48,
                "potion_type": [100, 0, 0, 0],
            }
        )
    elif num_green_potions > 0:
        catalog.append(
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": num_green_potions,
                "price": 48,
                "potion_type": [0, 100, 0, 0],
            }
        )
    elif num_blue_potions > 0:
        catalog.append(
            {
                "sku": "BLUE_POTION_0",
                "name": "blue potion",
                "quantity": num_blue_potions,
                "price": 58,
                "potion_type": [0, 0, 100, 0],
            }
        )
    
    print(f"catalog: {catalog}")
    return catalog
