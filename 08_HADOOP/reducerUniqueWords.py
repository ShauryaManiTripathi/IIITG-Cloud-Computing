#!/usr/bin/env python3
import sys

unique_words = set()

for line in sys.stdin:
    word, _ = line.strip().split('\t')
    unique_words.add(word)

for word in unique_words:
    print(word)
