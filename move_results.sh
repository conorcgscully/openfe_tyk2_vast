#!/bin/bash

# Script to move all directories and JSON files starting with "lig_" to results directory

# Create results directory if it doesn't exist
mkdir -p results

# Counter for moved items
moved_count=0

echo "Moving directories and JSON files with pattern 'lig_*' to results/"

# Move directories starting with lig_
for dir in lig_*/; do
    if [ -d "$dir" ]; then
        echo "Moving directory: $dir"
        mv "$dir" results/
        ((moved_count++))
    fi
done

# Move JSON files starting with lig_
for file in lig_*.json; do
    if [ -f "$file" ]; then
        echo "Moving JSON file: $file"
        mv "$file" results/
        ((moved_count++))
    fi
done

echo "Done! Moved $moved_count items to results/"

