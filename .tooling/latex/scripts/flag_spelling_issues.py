#!/usr/bin/env python3

# This script compares each markdown paragraph found in all *.text files
# in the project that contain a spelling issue, marks the issue, and saves
# to a log file.

##################
# Assign variables

# If flag_spelling_last_run.txt exists, check for the last time this script ran
# If flag_spelling_last_run.txt exists:
#     time_last_run = first line of timestamp.txt saved as time stamp number
# else: 
#	    time_last_run = January 1, 1900
#
# results = ./log/flag_spelling_(timestamp).txt
# log_file = ./log/flag_spelling_(timestamp).log
# spelling_issues = ../dictionaries/spelling-errors-list.txt
##################

##################
# Iterate through each *.text file with time stamp of last save
# newer than time_last_run

# For each file: #append to results
#    print() # appended to results
#    print('#' * 20) 
#    print('#' * 20) 
#    print(path/and/filename)
#    print()
#    If paragraph contains unmarked spelling issue:
#        ignore text between _XYZ_ _XYZ_
#        mark spelling issue as _XYZ_spelling-issue_XYZ_
#        append paragraph to results
#    print()
#    close file
##################

##################
# Update flag_spelling_last_run.txt with current timestamp.
##################
    




