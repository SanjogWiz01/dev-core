def factorial(number):
    """Return the factorial of a non-negative integer using recursion."""
    if number < 0:
        raise ValueError("factorial is not defined for negative numbers")

    if number == 0 or number == 1:
        return 1

    return number * factorial(number - 1)


if __name__ == "__main__":
    value = 5
    result = factorial(value)
    print(f"The factorial of {value} is {result}")
