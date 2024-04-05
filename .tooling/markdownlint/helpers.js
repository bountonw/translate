import fs from "fs";
import path from "path";
import { forEachLine, getLineMetadata } from "markdownlint-rule-helpers";

const clamp = (number, min, max) => {
  return Math.max(min, Math.min(number, max));
};

export const extractContext = (line, column) => {
  const contextPadding = 10;
  return line.substr(
    clamp(column - contextPadding, 0, line.length - 1),
    contextPadding * 2
  );
};

export const readForbiddenTerms = (language) =>
  fs
    .readFileSync(
      path.resolve(".tooling/markdownlint", `./forbidden_terms/${language}`),
      "utf-8"
    )
    .split("\n")
    .filter((l) => l && l.charAt(0) !== "#");

export const applyCustomFormattingRules =
  (customFormattingRules) => (params, onError) => {
    forEachLine(getLineMetadata(params), (line, lineIndex) => {
      for (const rule of customFormattingRules) {
        const { name, regexp, test } = rule;
        const column = test ? test(line, params) : line.search(regexp);
        if (column >= 0) {
          onError({
            lineNumber: lineIndex + 1,
            detail: `Found ${name} at column ${column}`,
            context: extractContext(line, column),
            range: [column + 1, 1],
          });
        }
      }
    });
  };
