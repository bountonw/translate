#!/bin/bash

echo "Making full book PDF including individual chapter PDFs for each chapter..."


# https://stackoverflow.com/a/7069755/3938401
use_existing_tex_files=false
while test $# -gt 0; do
  case "$1" in
    --use-existing-tex-files)
      use_existing_tex_files=true
      echo "Skipping remake of individual chapter tex files..."
      shift
      ;;
    *)
      break
      ;;
  esac
done

CHAP_NUM=42 # set to 42 for full book or a small number for testing
if [ "${use_existing_tex_files}" = false ]
then
    for ((i=1;i<=CHAP_NUM;i++)); do
        echo "Processing chapter ${i}..."
        chapNum=$(printf "%02d" $i) # leading 0 for chapters 1-9
        scripts/make_pdf.sh "GC${chapNum}"
        # Run LuaLaTeX with output directory
        echo "Making PDF for chapter ${i}..."
        if ! lualatex -output-directory=pdf/logs "temp/tex/GC${chapNum}.tex"; then
            echo "ERROR: LuaLaTeX failed for chapter ${chapNum}.tex"
            exit 1
        fi
        # Move the PDF to the main pdf folder
        if [[ -f "pdf/logs/GC${chapNum}.pdf" ]]; then
            mv "pdf/logs/GC${chapNum}.pdf" "pdf/GC${chapNum}.pdf"
        else
            echo
            echo "ERROR: PDF for chapter ${chapNum} was not generated"
            exit 1
        fi
    done
fi

echo "All chapters processed, now combining into one giant PDF"

echo "Verifying that all chapters got made..."
for ((i=1;i<=CHAP_NUM;i++)); do
    echo "Checking for file for chapter $i..."
    chapNum=$(printf "%02d" $i) # leading 0 for chapters 1-9
    fileName="GC${chapNum}_lo_stage2.tex"
    if [ ! -f "temp/${fileName}" ]; then
        echo "File ${fileName} not found!"
        exit -1
    fi
done

echo "Running Module 3 to create one giant book..."
chapNumLeadingZero=$(printf "%02d" $CHAP_NUM)
if ! python3 scripts/module3_preprocess.py "GC[01..${chapNumLeadingZero}]" --debug --full; then
    echo "ERROR: Module 3 failed for $1"
    exit 1
fi

echo "Running LuaLaTeX..."
# Create output directories
mkdir -p pdf/logs

# Run lualatex with output directory
if ! lualatex -output-directory=pdf/logs "temp/tex/full-output.tex"; then
    echo "ERROR: LuaLaTeX failed for full-output.tex"
    exit 1
fi

# Move the PDF to the main pdf folder
if [[ -f "pdf/logs/full-output.pdf" ]]; then
    mv "pdf/logs/full-output.pdf" "pdf/GC_lo_full.pdf"
else
    echo
    echo "ERROR: PDF was not generated"
    exit 1
fi

echo -e "SUCCESS: PDF generated for full book"

# Open pdf
okular "pdf/${1}.pdf" &
