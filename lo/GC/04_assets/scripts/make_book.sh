#!/bin/bash

# All build output (temp files, chapter and book PDFs, logs) goes under one ignored folder.
BUILD="scripts/build"

echo "Making full book PDF including individual chapter PDFs for each chapter..."


# https://stackoverflow.com/a/7069755/3938401
use_existing_tex_files=false
debug_flag=""
CHAP_NUM=42 # set to 42 for full book or a small number for testing
while test $# -gt 0; do
  case "$1" in
    --use-existing-tex-files)
      use_existing_tex_files=true
      echo "Skipping remake of individual chapter tex files..."
      shift
      ;;
    --debug)
      debug_flag="--debug"
      shift
      ;;
    --max-chapter-override)
      shift
      CHAP_NUM=$1
      echo "Adjusted max chapter number to ${CHAP_NUM}"
      shift
      ;;
    *)
      break
      ;;
  esac
done

timestamp=$(date +%Y_%m_%d__%H_%M_%S) # year_month_date__hour_minute_second
logfolder="${BUILD}/pdf/logs/${timestamp}"

# Now make introduction
if [ "${use_existing_tex_files}" = false ]
then
    mkdir -p "${logfolder}" # make if does not exist already; logs are only output (right now) by make_pdf
    # so don't need folder made if using existing tex files
    for ((i=1;i<=CHAP_NUM;i++)); do
        echo "Processing chapter ${i}..."
        chapNum=$(printf "%02d" $i) # leading 0 for chapters 1-9
        scripts/make_pdf.sh "GC${chapNum}" ${debug_flag} --log-folder "${logfolder}"
        # Run LuaLaTeX with output directory
        echo "Making PDF for chapter ${i}..."
        if ! lualatex -output-directory=${BUILD}/pdf/logs "${BUILD}/temp/tex/GC${chapNum}.tex"; then
            echo "ERROR: LuaLaTeX failed for chapter ${chapNum}.tex"
            exit 1
        fi
        # Move the PDF to the main pdf folder
        if [[ -f "${BUILD}/pdf/logs/GC${chapNum}.pdf" ]]; then
            mv "${BUILD}/pdf/logs/GC${chapNum}.pdf" "${BUILD}/pdf/GC${chapNum}.pdf"
        else
            echo
            echo "ERROR: PDF for chapter ${chapNum} was not generated"
            exit 1
        fi
    done
fi

# Now make introduction
if [ "${use_existing_tex_files}" = false ]; then
    echo "Processing intro..."
    scripts/make_pdf.sh "GC00_introduction" ${debug_flag} --log-folder "${logfolder}"
    # Run LuaLaTeX with output directory
    echo "Making PDF for chapter ${i}..."
    if ! lualatex -output-directory=${BUILD}/pdf/logs "${BUILD}/temp/tex/GC00_introduction.tex"; then
        echo "ERROR: LuaLaTeX failed for introduction.tex"
        exit 1
    fi
    # Move the PDF to the main pdf folder
    if [[ -f "${BUILD}/pdf/logs/GC00_introduction.pdf" ]]; then
        mv "${BUILD}/pdf/logs/GC00_introduction.pdf" "${BUILD}/pdf/GC00_introduction.pdf"
    else
        echo
        echo "ERROR: PDF for introduction was not generated"
        exit 1
    fi
fi

echo "All chapters processed, now combining into one giant PDF"

echo "Verifying that all chapters got made..."
for ((i=1;i<=CHAP_NUM;i++)); do
    echo "Checking for file for chapter $i..."
    chapNum=$(printf "%02d" $i) # leading 0 for chapters 1-9
    fileName="GC${chapNum}_lo_stage2.tex"
    if [ ! -f "${BUILD}/temp/${fileName}" ]; then
        echo "File ${fileName} not found!"
        exit -1
    fi
done

echo "Verifying that intro file got made..."
fileName="GC00_introduction_lo_stage2.tex"
if [ ! -f "${BUILD}/temp/${fileName}" ]; then
    echo "File ${fileName} not found!"
    exit -1
fi

echo "Running Module 3 to create one giant book..."
chapNumLeadingZero=$(printf "%02d" $CHAP_NUM)
if ! python3 scripts/module3_preprocess.py "GC[01..${chapNumLeadingZero}]" ${debug_flag} --full; then
    echo "ERROR: Module 3 failed for $1"
    exit 1
fi

echo "Running LuaLaTeX..."
# Create output directories
mkdir -p ${BUILD}/pdf/logs

# Run lualatex with output directory (first pass - generates .toc file)
if ! lualatex -output-directory=${BUILD}/pdf/logs "${BUILD}/temp/tex/full-output.tex"; then
    echo "ERROR: LuaLaTeX failed for full-output.tex (first pass)"
    exit 1
fi

# Run lualatex second pass to build TOC
echo "Running LuaLaTeX second pass for TOC..."
if ! lualatex -output-directory=${BUILD}/pdf/logs "${BUILD}/temp/tex/full-output.tex"; then
    echo "ERROR: LuaLaTeX failed for full-output.tex (second pass)"
    exit 1
fi

# Move the PDF to the main pdf folder
if [[ -f "${BUILD}/pdf/logs/full-output.pdf" ]]; then
    mv "${BUILD}/pdf/logs/full-output.pdf" "${BUILD}/pdf/GC_lo_full.pdf"
else
    echo
    echo "ERROR: PDF was not generated"
    exit 1
fi

echo -e "SUCCESS: PDF generated for full book"

# Open pdf
okular "${BUILD}/pdf/GC_lo_full.pdf" &
