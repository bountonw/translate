#!/usr/bin/env bash

(cd ../../ && find . -path "*/th/LBF/03_public/*" -name "*.md") | while read LINE;
do
    f="$(echo $LINE | cut -c 3-)"
    if [[ "$f" == *".md" ]];then
        echo $f
        make lbf/${f%.*}.icml
    fi
done
