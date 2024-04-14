import { applyCustomFormattingRules } from "./helpers.js";

const customFormattingRules = [
  {
    name: "invalid spacing",
    test: (line) => {
      const doubleSpaceIndex = line ? line.search(/\S\s{2,}($|\S)/) : -1;
      if (doubleSpaceIndex !== -1) {
        const isAllowedDoubleSpaceForPoetry =
          line.search(/>\s/) !== -1 &&
          line
            .replace(/^>/, "")
            .trim()
            .search(/\S\s{2,}($|\S)/) === -1;
        return isAllowedDoubleSpaceForPoetry ? -1 : doubleSpaceIndex;
      }
      return -1;
    },
  },
  {
    name: "no space before '{'",
    regexp: /\S{/,
  },
  {
    name: "missing space before opening curly quotes",
    regexp: /[^\s“‘\()][“‘]/,
  },
  {
    name: "invalid space after opening curly quotes",
    regexp: /[“‘]\s/,
  },
  {
    name: "invalid space before closing curly quotes",
    regexp: /\s[”’]/,
  },
  {
    name: "missing space after closing curly quotes",
    regexp: /(\w”[^\s<’”—\[\)…]|(?<![a-z])’[^\s<”—\.\[\)…](?!s))/,
  },
  {
    name: "semicolon followed by a number",
    regexp: /;\d/,
  },
  {
    name: "hyphen instead of en-dash",
    regexp: /\d(-|—)\d/,
  },
  {
    name: "invalid reference code",
    test: (line, params) => {
      const { name: filename, lines } = params;
      if (
        line &&
        filename.search("/assets/") === -1 && // Ignore assets files
        line.search(/^(?!(#+|\{|\[\^\d\]|\s{4}|$))/) === 0
      ) {
        const lineIndex = lines.findIndex((l) => l === line);
        const nextLine = lines[lineIndex + 1] || lines[lineIndex + 2];
        const isFollowingLinePoetry =
          nextLine && nextLine.search(/^(>\s|\s{4,}\S+)/) === 0;
        return isFollowingLinePoetry ||
          line.search(/\{\w+ \d{1,3}\.\d{1,2}\}$/) >= 0
          ? -1
          : line.length - 1;
      }
      return -1;
    },
  },
];

const CustomFormatting = {
  names: ["custom-formatting"],
  description: "Custom formatting rules",
  tags: ["style"],
  function: applyCustomFormattingRules(customFormattingRules),
};

export default CustomFormatting;
