import sys
from collections import Counter

k = 3
distances = []

for line in sys.stdin:
    distance, label = line.strip().split('\t')
    distances.append((float(distance), label))

distances = sorted(distances)[:k]
nearest_labels = [label for _, label in distances]

most_common_label = Counter(nearest_labels).most_common(1)[0][0]
print(f"Predicted label: {most_common_label}")

