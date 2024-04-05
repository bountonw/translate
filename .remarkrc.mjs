import remarkFrontmatter from "remark-frontmatter";
import remarkLintFrontmatterSchema from "remark-lint-frontmatter-schema";

const remarkConfig = {
  plugins: [
    remarkFrontmatter,
    [
      remarkLintFrontmatterSchema,
      {
        schemas: {
          "./frontmatter-schema-lo.yaml": [
            "./lo/**/01_raw/*.md",
            "./lo/**/02_edit/*.md",
            "./lo/**/03_public/*.md",
          ],
          "./frontmatter-schema-th.yaml": [
            "./th/**/01_raw/*.md",
            "./th/**/02_edit/*.md",
            "./th/**/03_public/*.md",
          ],
        },
      },
    ],
  ],
};
export default remarkConfig;
