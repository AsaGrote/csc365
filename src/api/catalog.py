from fastapi import APIRouter

import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    
    catalog = []
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT id, name, num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, price, quantity from potion_mixtures"))
        
        for row in result:
            catalog.append(
                {
                    "sku": f"POTION_{row[0]}",
                    "name": f"{row[1]} potion",
                    "quantity": row[7],
                    "price": row[6],
                    "potion_type": [row[2], row[3], row[4], row[5]]
                }
            )
    
    print(f"catalog: {catalog}")
    return catalog
