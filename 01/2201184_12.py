class iiitg:
    def __init__(self, input_list):
        self.input_list = input_list

    def apply(self, func):
        try:
            return func(self.input_list)
        except Exception as e:
            raise Exception("Error occurred while applying the function: " + str(e))
        
squarelist = lambda x: [i**2 for i in x]

squares=iiitg([1,2,3,4,5,6,7,8,9,10]).apply(squarelist)
print(squares)