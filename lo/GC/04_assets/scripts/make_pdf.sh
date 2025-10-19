#!/bin/bash

# Check if filename was provided
if [[ -z "$1" ]]; then
    echo "Error: No filename provided"
    echo "Usage: ./make_pdf.sh GC01"
    exit 1
fi

echo -e "Processing $1 through the pipeline..."

# Module 1
echo -e "\nRunning Module 1...\n"
if ! python3 scripts/module1_preprocess.py "$1" --debug; then
    echo "ERROR: Module 1 failed for $1"
    exit 1
fi

# Module 2  
echo -e "\nRunning Module 2...\n"
if ! python3 scripts/module2_preprocess.py "$1" --debug; then
    echo "ERROR: Module 2 failed for $1"
    exit 1
fi

# Module 3
echo -e "\nRunning Module 3...\n"
if ! python3 scripts/module3_preprocess.py "$1" --debug; then
    echo "ERROR: Module 3 failed for $1"
    exit 1
fi

# LuaLaTeX
echo -e "\nRunning LuaLaTeX...\n"

# Create output directories
mkdir -p pdf/logs

# Run lualatex with output directory
if ! lualatex -output-directory=pdf/logs "temp/tex/${1}.tex"; then
    echo "ERROR: LuaLaTeX failed for ${1}.tex"
    exit 1
fi

# Move the PDF to the main pdf folder
if [[ -f "pdf/logs/${1}.pdf" ]]; then
    mv "pdf/logs/${1}.pdf" "pdf/${1}.pdf"
else
    echo
    echo "ERROR: PDF was not generated"
    exit 1
fi

echo -e "SUCCESS: PDF generated for $1"

# Open pdf
okular "pdf/${1}.pdf" &
