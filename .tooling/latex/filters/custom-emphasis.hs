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

main = toJSONFilter customEmphasis
  where customEmphasis (Emph xs)   = [latex "\\Emph{"  ] ++ xs ++ [latex "}"]
        customEmphasis (Strong xs) = [latex "\\Strong{"] ++ xs ++ [latex "}"]
        customEmphasis x           = [x]
        latex                      = RawInline (Format "latex")

