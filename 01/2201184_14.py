import functools

def find_product(numbers):
    def multiply(x,y):
        return x*y
    product = functools.reduce(multiply, numbers)
    #product = functools.reduce(lambda x, y: x * y, numbers)
    return product

# Example usage
input_list = [1, 2, 3, 4, 5]
result = find_product(input_list)
print(result),