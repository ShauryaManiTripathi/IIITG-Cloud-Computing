import sys
from collections import Counter

k = 3  # Number of nearest neighbors
distances = []

# Reducer: reads <distance, label> pairs from stdin
for line in sys.stdin:
    distance, label = line.strip().split('\t')
    distances.append((float(distance), label))

# Sort distances and select the k nearest neighbors
distances = sorted(distances)[:k]
nearest_labels = [label for _, label in distances]

# Determine the majority label among k nearest neighbors
most_common_label = Counter(nearest_labels).most_common(1)[0][0]
print(f"Predicted label: {most_common_label}")

