import { useConfig } from "nextra-theme-docs";

export default {
  logo: <span>แสงแห่งความจริง</span>,
  project: {
    link: "https://github.com/bountonw/translate",
  },
  editLink: {
    component: null
  },
  feedback: {
    content: ({ children }) => {
      const {frontMatter} = useConfig();
      return frontMatter.lastUpdated ? <>
        <div class="_mt-4 _mb-4 _block _text-xs _text-gray-500 dark:_text-gray-400">
          Content last updated on {frontMatter.lastUpdated}
        </div>
        {children}
      </> : null;
    }
  },
  search: false,
  footer: {
    content: (
      <span>
        This translation is licensed under a{' '}
        <a href="https://github.com/bountonw/translate/blob/main/LICENSE" target="_blank">Creative Commons Attribution-NoDerivs 4.0 International License</a>.
      </span>
    )
  },
};

// TODO: noindex
