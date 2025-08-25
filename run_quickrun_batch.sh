#!/bin/bash

# Script to run openfe quickrun on all .json files in tyk2_json directory
# and echo completion status for each iteration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JSON_DIR="$SCRIPT_DIR/tyk2_json"

# Check if tyk2_json directory exists
if [ ! -d "$JSON_DIR" ]; then
    echo "Error: tyk2_json directory not found at $JSON_DIR"
    exit 1
fi

# Count total number of .json files
total_files=$(find "$JSON_DIR" -name "*.json" | wc -l)
echo "Found $total_files .json files to process"
echo "Starting batch processing..."
echo

counter=0

# Loop through all .json files in the directory
for json_file in "$JSON_DIR"/*.json; do
    if [ -f "$json_file" ]; then
        counter=$((counter + 1))
        filename=$(basename "$json_file")
        oname="${filename%.json}"
        
        echo "[$counter/$total_files] Processing: $filename"
        
        # Check if output file already exists
        if [ -f "${oname}_result.json" ]; then
            echo "⏭ Skipping: ${oname}_result.json already exists"
        else
            echo "Running: openfe quickrun $json_file -o ${oname}_result.json" 
            
            # Run openfe quickrun on the current file
            openfe quickrun "$json_file" -o "${oname}_result.json" -d "$oname"
            exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                echo "✓ Completed successfully: $filename"
            else
                echo "✗ Failed with exit code $exit_code: $filename"
            fi
        fi
        
        echo "----------------------------------------"
    fi
done

echo
echo "Batch processing complete!"
echo "Processed $counter out of $total_files files"