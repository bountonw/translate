-- custom-emphasis.hs
{--
  Default behaviour:
     *...*   _..._  -> \emph{...}
    **...** __...__ -> \textbf{...}
  Filtered behaviour:
     *...*   _..._  -> \Emph{...}
    **...** __...__ -> \Strong{...}
--}

import Text.Pandoc
import Text.Pandoc.JSON

main = toJSONFilter inlineLatex
  where inlineLatex (Emph xs) =
          [latex "\\Emph{"  ] ++ xs ++ [latex "}"]
        inlineLatex (Strong xs) =
          [latex "\\Strong{"] ++ xs ++ [latex "}"]
        inlineLatex s@(Span (id, as, kps) xs) =
          case as of
            ["th"] -> [latex "{\\rmfamily "] ++ xs ++ [latex "}"]
            ["tag", "paragraph"] -> [latex "\\TagPar{"] ++ xs ++ [latex "}"]
            ["tag", "version"] -> [latex "\\TagVer{"] ++ xs ++ [latex "}"]
            ["basedon"] -> [latex "\\BasedOn{"] ++ xs ++ [latex "}"]
            _ -> [s]
        inlineLatex x = [x]
        latex = RawInline (Format "latex")

