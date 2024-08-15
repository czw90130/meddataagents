def gcd(a, b):
    """
    Calculate the Greatest Common Divisor of a and b using the Euclidean algorithm.
    
    Args:
    a (int): A positive integer
    b (int): A positive integer
    
    Returns:
    int: The Greatest Common Divisor of a and b
    
    Raises:
    ValueError: If inputs are not positive integers
    """
    # Input validation
    if not (isinstance(a, int) and isinstance(b, int)):
        raise ValueError("Both inputs must be integers")
    if a <= 0 or b <= 0:
        raise ValueError("Both inputs must be positive integers")
    
    # Euclidean algorithm
    while b != 0:
        a, b = b, a % b
    return a

def main():
    # Example usage
    print(f"GCD of 48 and 18 is: {gcd(48, 18)}")
    print(f"GCD of 100 and 75 is: {gcd(100, 75)}")
    
    # Error handling example
    try:
        print(f"GCD of -30 and 15 is: {gcd(-30, 15)}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
