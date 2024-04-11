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
    num_green_potions = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_green_potions from global_inventory"))
        num_green_potions = result.scalar_one()

    if num_green_potions > 0:
        return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": 1,
                "price": 48,
                "potion_type": [0, 100, 0, 0],
            }
        ]
    else:
        return []
