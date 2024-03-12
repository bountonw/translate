-- local logging = require 'logging'

function CodeBlock (block)
    -- logging.temp('pandoc', block)
    return pandoc.BlockQuote(block.text)
  end

-- TODO: transform quote indentation to nested quotes?
