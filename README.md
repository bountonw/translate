# Directory structure of the translation files

* Language: Top-level directory representing the language.
* Book: Subdirectory for each book.
* Volume (Optional): Subdirectory under each book, used if the original book is divided into smaller volumes.
* Translation Stages: Each book or volume contains the following subdirectories:

```
00_source: Contains the source files for each chapter.
01_raw: Initial, rough translations. These are preliminary and not intended for general reading.
02_edit: Improved translations with more refined language. Feedback is welcome at this stage.
03_public: Final translations ready for public distribution.
04_pdf: PDF renders of finished translations. These may be at any typesetting stage, and are named according to the following pattern: `[book code]_[timestamp]_[optional description].pdf`, e.g., `LBF_202405201218_font-test.pdf`. The optional description will be added to indicate any post-render processing that has been done, such as `_highlights`, `_suggestions`, etc. Additional description may be added to the commit message to indicate in greater detail the changes, suggestions, or status of the PDF.
```

## Developer

local `sandbox/` folders are ignored
