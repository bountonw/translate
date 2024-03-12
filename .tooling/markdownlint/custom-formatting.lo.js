import { applyCustomFormattingRules, readForbiddenTerms } from "./helpers.js";

const customFormattingRules = [
  {
    name: "forbidden term",
    regexp: new RegExp(`${readForbiddenTerms("lao.txt").join("|")}`),
  },
];

const CustomFormatting = {
  names: ["custom-formatting-lo"],
  description: "Custom formatting (lo) rules",
  tags: ["style"],
  function: applyCustomFormattingRules(customFormattingRules),
};

export default CustomFormatting;
