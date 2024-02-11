function stripParagraphHeadings(mdFile, outputFile)
  local strippedContent = ""

  for line in io.lines(mdFile) do
    if not string.match(line, "^## %b{}") and not string.match(line, "^$") then
      strippedContent = strippedContent .. line .. "\n"
    end
  end

  local f = io.open(outputFile, "w")
  if f then
    f:write(strippedContent)
    f:close()
    print("Stripped content saved to", outputFile)
  else
    print("Error opening output file:", outputFile)
  end
end

-- Specify input and output filenames
stripParagraphHeadings("source/GC/GC01_en.md", "source/stripped/GC/GC01_en.md")
