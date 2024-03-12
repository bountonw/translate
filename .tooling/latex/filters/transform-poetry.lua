-- local logging = require 'logging'

function CodeBlock (block)
    -- logging.temp('pandoc', pandoc.read('| ' .. block.text:gsub('\n', '\n| '), 'markdown').blocks[1])
    return pandoc.read('| ' .. block.text:gsub('\n', '\n| '), 'markdown').blocks[1]
  end

-- TODO: transform quote indentation to nested quotes?
