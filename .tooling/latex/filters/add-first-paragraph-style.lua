traverse = 'topdown'

function Blocks (blocks)
    local found_first_paragraph = false
    local blocks_new = {}
    for k,v in pairs(blocks) do
        if not found_first_paragraph and v.t == 'Para' then
            blocks_new[k] = pandoc.Div(v, { ["custom-style"] = 'First'})
            found_first_paragraph = true
        else
            blocks_new[k] = v
        end
    end
    return blocks_new, false
end
