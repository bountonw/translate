import { forEachLine, getLineMetadata } from "markdownlint-rule-helpers";
import fs from "fs";
import path from "path";
const forbiddenTerms = fs
  .readFileSync(
    path.resolve(".tooling/markdownlint", "./forbidden_lao_terms.txt"),
    "utf-8"
  )
  .split("\n")
  .filter((l) => l && l.charAt(0) !== "#");

const customFormattingRules = [
  {
    name: "forbidden term",
    regexp: new RegExp(`${forbiddenTerms.join("|")}`),
  },
];

const clamp = (number, min, max) => {
  return Math.max(min, Math.min(number, max));
};

const extractContext = (line, column) => {
  const contextPadding = 10;
  return line.substr(
    clamp(column - contextPadding, 0, line.length - 1),
    contextPadding * 2
  );
};

const CustomFormatting = {
  names: ["custom-formatting-lo"],
  description: "Custom formatting (lo) rules",
  tags: ["style"],
  function: (params, onError) => {
    forEachLine(getLineMetadata(params), (line, lineIndex) => {
      for (const rule of customFormattingRules) {
        const { name, regexp } = rule;
        const column = line.search(regexp);
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
  },
};

export default CustomFormatting;
