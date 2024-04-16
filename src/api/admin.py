from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from src.api.carts import reset_carts


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
                SET num_red_potions = 0, 
                    num_green_potions = 0, 
                    num_blue_potions = 0, 
                    num_red_ml = 0, 
                    num_green_ml = 0, 
                    num_blue_ml = 0, 
                    gold = 100"""))
    
    # Reset carts
    reset_carts()
    
    return "OK"

