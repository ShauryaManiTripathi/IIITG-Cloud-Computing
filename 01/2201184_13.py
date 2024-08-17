listofwords=['tare','hai','chand','ke','niche']

#use funtools.reduce , make upper case all
# import functools
# def funct(a,b):
#     if isinstance(a,list):
#         return a+[b.upper()]
#     else:
#         return [a.upper()]+[b.upper()]
#capitalized = functools.reduce(funct, listofwords)
#capitalized = functools.reduce(lambda a, b: a+[b.upper()] if isinstance(a, list) else [a.upper()]+[b.upper()], listofwords)


#use functool.map, make upper case all
capitalized = list(map(lambda x: x.upper(), listofwords))

print(capitalized)