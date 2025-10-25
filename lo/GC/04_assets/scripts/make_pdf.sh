#!/bin/bash

# Check if chaptername was provided
if [[ -z "$1" ]]; then
    echo "Error: No chaptername provided"
    echo "Usage: ./make_pdf.sh GC01"
    exit 1
fi

chaptername="${1}"
shift # bump off chapter number from args to test for others

logfolder=""
while test $# -gt 0; do
  case "$1" in
    --log-folder)
      shift # bump off --log-folder arg name
      logfolder=$1
      echo "Using log folder of: ${logfolder}"
      ;;
    *)
      break
      ;;
  esac
done

echo -e "Processing ${chaptername} through the pipeline..."

# Module 1
echo -e "\nRunning Module 1...\n"
if ! python3 scripts/module1_preprocess.py "${chaptername}" --debug; then
    echo "ERROR: Module 1 failed for ${chaptername}"
    exit 1
fi

# Module 2  
echo -e "\nRunning Module 2...\n"
if ! python3 scripts/module2_preprocess.py "${chaptername}" --debug; then
    echo "ERROR: Module 2 failed for ${chaptername}"
    exit 1
fi

# Module 3
echo -e "\nRunning Module 3...\n"
if ! python3 scripts/module3_preprocess.py "${chaptername}" --debug; then
    echo "ERROR: Module 3 failed for ${chaptername}"
    exit 1
fi

# LuaLaTeX
echo -e "\nRunning LuaLaTeX...\n"

# Create output directories
mkdir -p pdf/logs

# Run lualatex with output directory
if ! lualatex -output-directory=pdf/logs "temp/tex/${chaptername}.tex"; then
    echo "ERROR: LuaLaTeX failed for ${chaptername}.tex"
    exit 1
fi

# Move the PDF to the main pdf folder
if [[ -f "pdf/logs/${chaptername}.pdf" ]]; then
    mv "pdf/logs/${chaptername}.pdf" "pdf/${chaptername}.pdf"
else
    echo
    echo "ERROR: PDF was not generated"
    exit 1
fi

echo -e "SUCCESS: PDF generated for ${chaptername}"

# Open pdf
okular "pdf/${chaptername}.pdf" &
