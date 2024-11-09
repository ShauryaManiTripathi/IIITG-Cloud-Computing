import sys
import math

# Define a test data point for prediction
test_point = [5.1, 3.5, 1.4, 0.2]  # Adjust as needed
k = 3  # Number of nearest neighbors to consider

def calculate_distance(point1, point2):
    return math.sqrt(sum((float(x) - float(y))**2 for x, y in zip(point1, point2)))

# Mapper: reads from stdin, calculates distance, outputs <distance, label>
for line in sys.stdin:
    data = line.strip().split(',')
    features = list(map(float, data[:-1]))  # Extract numeric features as floats
    label = data[-1].strip('"')  # Species label (last column), stripped of quotes

    # Calculate distance to test_point and output <distance \t label>
    distance = calculate_distance(features, test_point)
    print(f"{distance}\t{label}")

