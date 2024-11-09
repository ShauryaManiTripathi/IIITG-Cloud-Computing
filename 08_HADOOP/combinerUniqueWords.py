#!/usr/bin/env python3
import sys

unique_words = set()
for line in sys.stdin:
    word, count = line.strip().split('\t')
    unique_words.add(word)

for word in unique_words:
    print(f"{word}\t1")

