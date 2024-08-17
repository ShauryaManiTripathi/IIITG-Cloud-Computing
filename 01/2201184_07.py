listofitems=[1,2,3,4,5,6,7,8,3]
dictofitems = {}
def firstduplicate(listofitems):
    for i in listofitems:
        if i in dictofitems:
            print(f"First duplicate is {i}")
            break
        else:
            dictofitems[i] = 1
firstduplicate(listofitems)