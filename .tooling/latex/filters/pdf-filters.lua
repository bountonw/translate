-- local logging = require 'logging'

local text = pandoc.text

-- Remove paragraph code headings
function Header(el)
    if el.level == 2 then
        return {}
    end
end

-- Transform CodeBlocks to BlockQuotes
function CodeBlock (el)
    -- logging.temp('pandoc', el)
    return pandoc.BlockQuote(el.text)
  end

-- TODO: transform quote indentation to nested quotes?
