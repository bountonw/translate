import { applyCustomFormattingRules } from "./helpers.js";

const customFormattingRules = [
  {
    name: "invalid spacing",
    regexp: /\S\s{2,}($|\S)/,
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
    regexp: /[’”][^\s<’”—\.\[\)]/,
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
        const nextLine = lines[lines.findIndex((l) => l === line) + 1];
        const isNextLinePoetry = nextLine && nextLine.search(/^\s{4}/) === 0;
        return isNextLinePoetry || line.search(/\{\w+ \d{1,3}\.\d{1,2}\}$/) >= 0
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
