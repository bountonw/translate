#!/usr/bin/env bash

# TODO: nix fixed directory
SOURCEDIR=../../th/PP/PP1/03_public

for f in ${SOURCEDIR}*
do
    t=`basename $f`
    make draft/${t%.*}.pdf
    echo $t
done
