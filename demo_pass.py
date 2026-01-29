"""Module for calculating totals."""

def calculate_total(items):
    """
    Calculate the total sum of numeric values.
    
    Args:
        items (list): List of numeric values to sum
        
    Returns:
        float: Sum of all items in the list
        
    Raises:
        ValueError: If the items list is empty
        TypeError: If non-numeric values are provided
    """
    if not items:
        raise ValueError("Cannot calculate total of empty list")
    
    if not all(isinstance(x, (int, float)) for x in items):
        raise TypeError("All values must be numeric")
    
    return sum(items)