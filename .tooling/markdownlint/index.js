#!/usr/bin/env node

import { globby } from "globby";
import markdownlint from "markdownlint";

const GLOBAL_CONFIG = {
  "fenced-code-language": false,
  "line-length": false,
  "no-bare-urls": false,
  "no-duplicate-heading": false,
  "no-inline-html": false,
  "no-trailing-punctuation": false,
  "single-trailing-newline": false,
  "heading-style": {
    style: "atx",
  },
};

const CHECKS = [
  {
    globPath: "./**/",
    customFormatting: "custom-formatting.js",
    config: GLOBAL_CONFIG,
  },
  {
    globPath: "./**/03_public/",
    customFormatting: "custom-formatting-public.js",
    config: {
      default: false,
    },
  },
  {
    globPath: "./lo/**/",
    customFormatting: "custom-formatting.lo.js",
    config: {
      default: false,
    },
  },
  {
    globPath: "./th/**/",
    customFormatting: "custom-formatting.th.js",
    config: {
      default: false,
    },
  },
  {
    globPath: "./th/**/03_public/",
    customFormatting: "custom-formatting-public.th.js",
    config: {
      default: false,
    },
  },
];

(async () => {
  let allClear = true;
  for (const { globPath, customFormatting, config } of CHECKS) {
    const paths = await globby([
      `${globPath}/*.md`,
      "!node_modules",
      "!**/00_source/*.md",
      "!**/001_machineraw/*.md",
    ]);
    console.log(`Linting ${paths.length} files in "${globPath}"`);
    let customRules = [];
    if (customFormatting) {
      const { default: customRule } = await import(`./${customFormatting}`);
      customRules = [customRule];
    }
    const options = {
      files: paths,
      config: {
        ...config,
        ...(customRules.length && {
          [customRules[0].names[0]]: true,
        }),
      },
      customRules,
    };

    const result = markdownlint.sync(options);
    const stringResult = result.toString();
    if (stringResult) {
      console.log(stringResult);
      allClear = false;
    }
  }
  if (allClear) {
    console.log("All clear!");
  } else {
    process.exit(1);
  }
})();
