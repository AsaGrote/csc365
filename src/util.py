def get_ml_color_type(potion_type):
    if potion_type == [1, 0, 0, 0] or potion_type == [100, 0, 0, 0]:
        return 'RED'   
    elif potion_type == [0, 1, 0, 0] or potion_type == [0, 100, 0, 0]:
        return 'GREEN'
    elif potion_type == [0, 0, 1, 0] or potion_type == [0, 0, 100, 0]:
        return 'BLUE'
    elif potion_type == [0, 0, 0, 1] or potion_type == [0, 0, 0, 100]:
        return 'DARK'