from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    total_potions = 0
    total_ml = 0
    gold = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(change), 0) AS quantity 
            FROM potion_ledger
            LEFT JOIN potion_mixtures ON potion_mixtures.id = potion_ledger.potion_id
            """
        ))

        total_potions = result.scalar_one()
        
        result = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(change), 0) AS quantity 
            FROM ml_ledger
            """
        ))
        
        total_ml = result.scalar_one()
        
        result = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(change), 0) AS quantity 
            FROM gold_ledger
            """
        ))
        
        gold = result.scalar_one()
        
    return {"number_of_potions": total_potions, "ml_in_barrels": total_ml, "gold": gold}

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
