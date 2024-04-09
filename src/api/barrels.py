from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

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
    
    additional_ml_green = 0
    gold_spent = 0
    for barrel in barrels_delivered:
        if barrel.sku == "SMALL_GREEN_BARREL":
            additional_ml_green += barrel.ml_per_barrel*barrel.quantity
            gold_spent += barrel.price*barrel.quantity
            
    if additional_ml_green > 0:
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("SELECT * from global_inventory"))
            row = result.one()
            initial_green_ml = row[1]
            initial_gold = row[2]
            result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {initial_green_ml+additional_ml_green}, gold = {initial_gold-gold_spent}"))
    
    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    
    # Check if green barrels are offered
    green_barrel_obj = None
    for barrel in wholesale_catalog:
        if barrel.sku == "SMALL_GREEN_BARREL":
            green_barrel_obj = barrel
    
    # Check if green potion stock is low
    quantity_green_potion = 0
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * from global_inventory"))
        quantity_green_potion = result.scalar_one()

    if green_barrel_obj and quantity_green_potion < 10:
        return [
            {
                "sku": "SMALL_GREEN_BARREL",
                "quantity": 1
            }
        ]

    return []
