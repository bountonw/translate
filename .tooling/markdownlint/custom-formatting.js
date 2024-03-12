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
    name: "invalid space before closing curly quotes",
    regexp: /\s[”’]/,
  },
  {
    name: "semicolon followed by a number",
    regexp: /;\d/,
  },
  {
    name: "hyphen instead of en-dash",
    regexp: /\d(-|—)\d/,
  },
];

const CustomFormatting = {
  names: ["custom-formatting"],
  description: "Custom formatting rules",
  tags: ["style"],
  function: applyCustomFormattingRules(customFormattingRules),
};

export default CustomFormatting;
