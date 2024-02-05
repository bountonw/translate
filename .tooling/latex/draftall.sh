#!/usr/bin/env bash

# TODO: nix fixed directory
SOURCEDIR=../../th/PP/PP1/03_public/

for f in ${SOURCEDIR}*
do
    t=`basename $f`
    if [[ "$t" == *".md" ]];then
        echo $f
        make draft/${t%.*}.pdf
    fi
done
