n=int(input("Enter the number of elements: "))
def funcc(n):
    dictofitems = {}


    for i in range(n+1):
        dictofitems[i] = [i**2,i**3]
    return dictofitems

dictofitems=funcc(n)
for i in dictofitems:
    print(f"{i} : {dictofitems[i]}")