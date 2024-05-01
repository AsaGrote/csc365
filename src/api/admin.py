from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth


import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    
    # Reset database
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("DELETE FROM potion_ledger"))
        result = connection.execute(sqlalchemy.text("DELETE FROM ml_ledger"))
        result = connection.execute(sqlalchemy.text("DELETE FROM gold_ledger"))
        result = connection.execute(sqlalchemy.text(
            f"""INSERT INTO gold_ledger (description, change) 
                VALUES ('Initial gold', 100)"""
        ))
    
    return "OK"

