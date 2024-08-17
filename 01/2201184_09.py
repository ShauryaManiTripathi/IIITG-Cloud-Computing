def create_tuples(list1, list2):
    return list(zip(list1, list2))

list1 = [1, 2, 3, 4]
list2 = ['a', 'b', 'c', 'd']
result = create_tuples(list1, list2)
print(result)