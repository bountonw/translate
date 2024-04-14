import { applyCustomFormattingRules, readForbiddenTerms } from "./helpers.js";

const customFormattingRules = [
  {
    name: "forbidden term",
    regexp: new RegExp(`${readForbiddenTerms("thai.txt").join("|")}`),
  },
  {
    name: "invalid (ดู spacing",
    regexp: /\(ดู\S/,
  },
];

const CustomFormatting = {
  names: ["custom-formatting-th"],
  description: "Custom formatting (th) rules",
  tags: ["style"],
  function: applyCustomFormattingRules(customFormattingRules),
};

export default CustomFormatting;
