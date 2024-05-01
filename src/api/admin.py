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
        result = connection.execute(sqlalchemy.text(
            f"""UPDATE global_inventory 
                SET num_red_ml = 0, 
                    num_green_ml = 0, 
                    num_blue_ml = 0, 
                    gold = 100"""))
        
        result = connection.execute(sqlalchemy.text(
            f"""UPDATE potion_mixtures 
                SET quantity = 0"""))
    
    # Reset carts
    reset_carts()
    
    return "OK"

