-- local logging = require 'logging'

function ternary (cond, T, F)
    if cond then return T else return F end
end

function inlines_has_paragraph_code (inlines)
    return #inlines > 3
      and inlines[#inlines].t == "Str"
      and string.match(inlines[#inlines].text, '.}')
end

function Inlines (inlines)
    -- logging.temp('pandoc', #inlines, inlines[#inlines - 3])
    if inlines_has_paragraph_code(inlines) then
        local remove_from_index = ternary(inlines[#inlines - 3].t == 'Space', #inlines - 3, #inlines - 2) - 1
        -- logging.temp('pandoc', #inlines, remove_from_index)
        return pandoc.Inlines({table.unpack(inlines, 1, remove_from_index)})
    end
end
