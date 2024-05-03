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
        result = connection.execute(sqlalchemy.text(
            """SELECT COALESCE(SUM(change), 0) AS quantity, 
                    potion_mixtures.item_sku, potion_mixtures.name,
                    potion_mixtures.price, potion_mixtures.num_red_ml, 
                    potion_mixtures.num_green_ml, potion_mixtures.num_blue_ml,
                    potion_mixtures.num_dark_ml
               FROM potion_ledger
               LEFT JOIN potion_mixtures ON potion_mixtures.id = potion_ledger.potion_id
               GROUP BY potion_mixtures.item_sku, potion_mixtures.name,
                        potion_mixtures.price, potion_mixtures.num_red_ml, 
                        potion_mixtures.num_green_ml, potion_mixtures.num_blue_ml,
                        potion_mixtures.num_dark_ml"""))
        
        # TODO: add order and limit to 6 potions
        
        # TODO: reference things by name rather than index
        for row in result:
            catalog.append(
                {
                    "sku": row[1],
                    "name": row[2],
                    "quantity": row[0],
                    "price": row[3],
                    "potion_type": [row[4], row[5], row[6], row[7]]
                }
            )
    
    print(f"catalog: {catalog}")
    return catalog
