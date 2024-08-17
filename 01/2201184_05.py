listofitems=[1,2,3,4,2,4,5,6,7,8,9,10]
def dictofitems(listofitems):
    dictofitems = {}

    for i in listofitems:
        if i in dictofitems:
            dictofitems[i] += 1
        else:
            dictofitems[i] = 1
    return dictofitems

dictofitem=dictofitems(listofitems)
for i in dictofitem:
    print(f"{i} : {dictofitem[i]}")