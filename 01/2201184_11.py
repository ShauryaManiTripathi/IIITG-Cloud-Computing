n=10

funcc=lambda n:{i:i**2 for i in range(n+1)}
dictofitems=funcc(n)
for i in dictofitems:
    print(f"{i} : {dictofitems[i]}")