#!/usr/bin/env node

import fs from "fs";
import path from "path";
import matter from "gray-matter";
import child_process from "child_process";

const DOCS_PATH = "../th";
const PAGES_PATH = "./pages";

const getFolders = () => {
  const folders = fs
    .readdirSync(DOCS_PATH, { recursive: true })
    .filter((file) => {
      const stat = fs.statSync(path.join(DOCS_PATH, file));
      return stat && stat.isDirectory() && path.basename(file) === "03_public";
    });
  return folders;
};

const processFolder = (folder) => {
  const destinationDir = path.join(PAGES_PATH, path.dirname(folder));
  fs.mkdirSync(destinationDir, { recursive: true });

  // copy files
  const sourceDir = path.join(DOCS_PATH, folder);
  copyFiles(sourceDir, destinationDir);
};

const copyFiles = (sourceDir, destinationDir) => {
  fs.readdirSync(sourceDir, { recursive: true })
    .filter((file) => {
      const stat = fs.statSync(path.join(sourceDir, file));
      return stat && stat.isFile() && path.extname(file) === ".md";
    })
    .map((file) => {
      // This is only necessary because the filename will become the final URL slug
      const newFilename = file.replace(/[A-Z]+(.*)_th.md/, "$1.md");
      copyFile(
        path.join(sourceDir, file),
        path.join(destinationDir, newFilename)
      );
    });
};

const copyFile = (fromPath, toPath) => {
  const source = fs.readFileSync(fromPath, "utf-8");
  const matterObject = matter(source);
  const title = `${matterObject.data.chapter.number}. ${matterObject.data.chapter.title.th}`;
  const metadata = {
    ...matterObject.data,
    title,
    lastUpdated: child_process.execSync(
      `git log -n 1 --pretty=format:%cd --date=format:"%Y-%m-%d %H:%M%p" ${fromPath}`,
      { encoding: "utf-8" }
    ),
  };
  const content = `# ${title}

${matterObject.content.replace(/\n##\s+[^}]+\}/g, "")}`;

  fs.writeFileSync(toPath, matter.stringify(content, metadata));
};

// Run!
getFolders().map(processFolder);
