# test_perfect_docs.py
"""Module docstring for perfect documentation test."""

def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.
    
    Args:
        numbers (List[float]): List of numeric values to average
        
    Returns:
        float: The arithmetic mean of the input numbers
        
    Raises:
        ValueError: If the input list is empty
        TypeError: If non-numeric values are provided
    """
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")
    
    if not all(isinstance(x, (int, float)) for x in numbers):
        raise TypeError("All values must be numeric")
    
    return sum(numbers) / len(numbers)


def is_prime(n):
    """
    Check if a number is prime.
    
    Args:
        n (int): The number to check for primality
        
    Returns:
        bool: True if the number is prime, False otherwise
        
    Raises:
        ValueError: If n is less than 2
    """
    if n < 2:
        raise ValueError("Prime check requires n >= 2")
    
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


class DataProcessor:
    """
    A class for processing numerical data with validation.
    
    Attributes:
        data (List[float]): The stored numerical data
        name (str): Identifier for the processor instance
    """
    
    def __init__(self, data, name="processor"):
        """
        Initialize the DataProcessor with data.
        
        Args:
            data (List[float]): Initial data to store
            name (str): Name identifier for this processor
            
        Raises:
            ValueError: If data list is empty
            TypeError: If data contains non-numeric values
        """
        if not data:
            raise ValueError("Data cannot be empty")
        if not all(isinstance(x, (int, float)) for x in data):
            raise TypeError("All data values must be numeric")
        
        self.data = data
        self.name = name
    
    def get_statistics(self):
        """
        Get basic statistics for the stored data.
        
        Returns:
            Dict[str, float]: Dictionary containing 'mean', 'min', and 'max' values
        """
        return {
            "mean": sum(self.data) / len(self.data),
            "min": min(self.data),
            "max": max(self.data)
        }
    
    def filter_outliers(self, threshold=2.0):
        """
        Remove outliers from the data using z-score method.
        
        Args:
            threshold (float): Z-score threshold for outlier detection
            
        Yields:
            float: Non-outlier data points one at a time
        """
        if len(self.data) < 2:
            for item in self.data:
                yield item
            return
        
        mean = sum(self.data) / len(self.data)
        variance = sum((x - mean) ** 2 for x in self.data) / len(self.data)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            for item in self.data:
                yield item
        else:
            for item in self.data:
                z_score = abs((item - mean) / std_dev)
                if z_score <= threshold:
                    yield item