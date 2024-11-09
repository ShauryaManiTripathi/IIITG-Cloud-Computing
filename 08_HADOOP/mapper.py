#!/usr/bin python3.11
import sys
import re

pattern = re.compile(r'[A-Za-z]+|[^A-Za-z\s]+')

for line in sys.stdin:
    tokens = pattern.findall(line.strip())
    for token in tokens:
        print(f"{token}\t1")

