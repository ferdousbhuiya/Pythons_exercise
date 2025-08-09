
def add(x, y):
    return x + y
""" This function adds two numbers """
def subtract(x, y):
    return x - y
""" This function subtracts two numbers """
def multiply(x, y):
    return x * y
""" This function multiplies two numbers """

def divide(x, y):
    """
    This function divides two numbers.
    """ 
    if y != 0:
        return x / y
    else:
        return "Division by zero error" 
    