const { forEachLine, getLineMetadata } = require("markdownlint-rule-helpers");
const { config: draftConfig } = require("./config-draft.markdownlint-cli2.cjs");

const publicFormattingRules = [
  {
    name: "invalid spacing",
    regexp: /\S\s{2,}($|\S)/,
  },
  {
    name: "no space before '{'",
    regexp: /\)[^ ’”;:,.!\[]/,
  },
  {
    name: "closing parenthesis not properly followed",
    regexp: /\)[^ ’”;:,.!\[]/,
  },
  {
    name: "missing space after closing curly quotes",
    regexp: /[’”][^\s<’”—\.\[]/,
  },
  {
    name: "no trailing space after 'ๆ' mai yamok",
    regexp: /ๆ[^\s’”]/,
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

module.exports = {
  customRules: [
    {
      names: ["custom-formatting"],
      description: "Custom formatting rules",
      tags: ["style"],
      function: (params, onError) => {
        forEachLine(getLineMetadata(params), (line, lineIndex) => {
          for (const rule of publicFormattingRules) {
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
    },
  ],
  config: {
    ...draftConfig,
    "custom-formatting": true,
  },
  globs: ["**/03_public/**.md", "!node_modules"],
};
