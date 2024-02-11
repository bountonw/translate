function stripParagraphHeadings(mdFile)
  local strippedContent = ""

  for line in io.lines(mdFile) do
    if not string.match(line, "^## %b{}") and not string.match(line, "^$") then
      strippedContent = strippedContent .. line .. "\n"
    end
  end

  return strippedContent
end
