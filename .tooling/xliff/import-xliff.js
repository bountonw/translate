#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const xml2js = require("xml2js");

const SEGMENT_SEPARATOR = "<!-- #segment-separator -->";

const sourceDirs = [
  {
    from: ".tms/assets/__GC_lo/__cat_01_raw",
    to: "lo/GC/01_raw",
    filenameTemplate: "GC%chapter%_lo.md",
  },
  {
    from: ".tms/assets/__GC_lo/__cat_segmented_but_unused",
    to: "lo/GC/001_machineraw",
    filenameTemplate: "GC%chapter%_lo.md",
  },
];

const processTitle = (title) => {
  const titleChunks = title.split("—");
  return titleChunks[titleChunks.length - 1]
    .replace(/#/g, "")
    .replace("{b>", "")
    .replace("<b}", "")
    .trim();
};

(async () => {
  for (const { from, to, filenameTemplate } of sourceDirs) {
    const fromPath = path.resolve(__dirname, "../../", from);
    const files = fs.readdirSync(fromPath, "utf-8");
    const toPath = path.resolve(__dirname, "../../", to);
    fs.mkdirSync(toPath, { recursive: true });
    for (const file of files) {
      if (!file.includes(".mxliff")) {
        continue;
      }
      console.log("Processing file", file);
      const xliffString = fs.readFileSync(path.join(fromPath, file), "utf-8");

      const parser = new xml2js.Parser();
      const result = await parser.parseStringPromise(xliffString);

      const groups = result.xliff.file[0].body[0].group;
      console.log("Groups", groups.length);

      const paragraphGroups = {};
      for (const group of groups) {
        const paragraphId = +group["$"]["m:para-id"];
        if (!group["trans-unit"]) {
          continue;
        }
        for (const transUnit of group["trans-unit"]) {
          const transSource = transUnit["source"][0];
          const transTarget = transUnit["target"][0];

          if (!paragraphGroups[paragraphId]) {
            paragraphGroups[paragraphId] = [];
          }
          paragraphGroups[paragraphId].push({
            source: transSource,
            target: transTarget,
          });
        }
      }

      const outputChunks = [];
      for (
        let paragraphId = 0;
        paragraphId < Object.keys(paragraphGroups).length;
        paragraphId++
      ) {
        if (!paragraphGroups[paragraphId]) {
          console.log("Missing group", paragraphId);
          continue;
        }
        const { target } = paragraphGroups[paragraphId][0];
        if (!paragraphId) {
          const { source } = paragraphGroups[paragraphId][0];
          const loTitle = processTitle(target);
          const enTitle = processTitle(source);

          const number = +file.split(/[-_]/)[0].replace(/\D/g, "");
          outputChunks.push(`---
chapter:
  number: ${number}
  title:
    lo: ${loTitle}
    en: ${enTitle}
---`);
          continue;
        }
        const chunks = paragraphGroups[paragraphId].reduce((carry, group) => {
          if (group.source.includes("##")) {
            carry.push(`### ${processTitle(group.target)}`);
          } else if (group.source !== "{i>Page<i}") {
            if (!Array.isArray(carry[carry.length - 1])) {
              carry.push([]);
            }
            carry[carry.length - 1].push(
              group.target.replace(/[\r\n]/g, " ").replace(/\s{2,}/g, " ")
            );
          }
          return carry;
        }, []);
        for (const chunk of chunks) {
          if (typeof chunk === "string") {
            outputChunks.push(chunk);
          } else {
            const nextOutput = chunk;
            const roughParagraphReference = nextOutput[
              nextOutput.length - 1
            ].match(/(\{\w+\s?\d+\.\s?\d+\})/);
            if (!roughParagraphReference) {
              // This happens in cases where a paragraph is interrupted by a heading
              outputChunks.push(nextOutput.join(SEGMENT_SEPARATOR).trim());
              console.log("no ref", nextOutput, paragraphId);
              // process.exit();
              continue;
            }
            const [, bookCode, page, paragraph] =
              roughParagraphReference[1].match(
                /{(\d?\S+)\s?(\d+)\s?\.\s?(\d+)}/
              );
            const paragraphReference = `{${bookCode} ${page}.${paragraph}}`;
            outputChunks.push(`## ${paragraphReference}`);
            outputChunks.push(nextOutput.join(SEGMENT_SEPARATOR).trim());
          }
        }
      }
      const output = outputChunks.join("\n\n");
      // console.log('uotput', output);
      // process.exit();

      const toFilename = filenameTemplate.replace(
        "%chapter%",
        file.replace(/[^\d]/g, "")
      );
      fs.writeFileSync(path.join(toPath, toFilename), output);
      console.log("Finished");
    }
  }
  process.exit();
})();
