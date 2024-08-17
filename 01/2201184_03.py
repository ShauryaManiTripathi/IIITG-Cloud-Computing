
import random
n = 10
def funcc(n):
    listofn = []
    for i in range(n):
        listofn.append(random.randint(0,100))
    return listofn
print(funcc(n))