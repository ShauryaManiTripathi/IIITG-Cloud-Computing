import sys
import math

test_point = [5.1, 3.5, 1.4, 0.2]
k = 3

def calculate_distance(point1, point2):
    return math.sqrt(sum((float(x) - float(y))**2 for x, y in zip(point1, point2)))

for line in sys.stdin:
    data = line.strip().split(',')
    features = list(map(float, data[:-1]))
    label = data[-1].strip('"')

    distance = calculate_distance(features, test_point)
    print(f"{distance}\t{label}")

