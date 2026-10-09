#!/bin/bash

# All build output (temp files, chapter and book PDFs, logs) goes under one ignored folder.
BUILD="scripts/build"

# Check if chaptername was provided
if [[ -z "$1" ]]; then
    echo "Error: No chapter name provided"
    echo "Usage: ./make_pdf.sh GC01"
    exit 1
fi

chaptername="${1}"
shift # bump off chapter number from args to test for others

logfolder=""
debug_flag=""
use_existing_tex_files=false
while test $# -gt 0; do
  case "$1" in
    --log-folder)
        shift # bump off --log-folder arg name
        logfolder=$1
        echo "Using log folder of: ${logfolder}"
        mkdir -p "${logfolder}" # make if does not exist already
        ;;
    --use-existing-tex-files)
      use_existing_tex_files=true
      echo "Skipping remake of individual chapter tex files..."
      shift
      ;;
    --debug)
        debug_flag="--debug"
        shift
        ;;
    *)
        break
        ;;
  esac
done

echo -e "Processing ${chaptername} through the pipeline..."

if [ "${use_existing_tex_files}" = false ]
then
    # Module 1
    echo -e "\nRunning Module 1...\n"
    if ! python3 scripts/module1_preprocess.py "${chaptername}" ${debug_flag}; then
        echo "ERROR: Module 1 failed for ${chaptername}"
        exit 1
    fi

    # Module 2  
    echo -e "\nRunning Module 2...\n"
    if ! python3 scripts/module2_preprocess.py "${chaptername}" ${debug_flag} --log-folder "${logfolder}"; then
        echo "ERROR: Module 2 failed for ${chaptername}"
        exit 1
    fi

    # Module 3
    echo -e "\nRunning Module 3...\n"
    if ! python3 scripts/module3_preprocess.py "${chaptername}" ${debug_flag}; then
        echo "ERROR: Module 3 failed for ${chaptername}"
        exit 1
    fi
fi

# LuaLaTeX
echo -e "\nRunning LuaLaTeX...\n"

# Create output directories
mkdir -p ${BUILD}/pdf/logs

# Run lualatex with output directory
if ! lualatex -output-directory=${BUILD}/pdf/logs "${BUILD}/temp/tex/${chaptername}.tex"; then
    echo "ERROR: LuaLaTeX failed for ${chaptername}.tex"
    exit 1
fi

# Move the PDF to the main pdf folder
if [[ -f "${BUILD}/pdf/logs/${chaptername}.pdf" ]]; then
    mv "${BUILD}/pdf/logs/${chaptername}.pdf" "${BUILD}/pdf/${chaptername}.pdf"
else
    echo
    echo "ERROR: PDF was not generated"
    exit 1
fi

echo -e "SUCCESS: PDF generated for ${chaptername}"

# Open the PDF when run on its own; make_book.sh passes --log-folder and opens only the book
if [ -z "${logfolder}" ]; then
    okular "${BUILD}/pdf/${chaptername}.pdf" &
fi
