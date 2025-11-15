using System.Text.RegularExpressions;
using CommandLine;
using Markdig;

if (args.Length == 0)
{
    args = ["--help"];
}
try
{
    Parser.Default.ParseArguments<Options>(args)
        .WithParsed(ConvertFiles)
        .WithNotParsed(HandleParseError);
}
catch (Exception e)
{
    Console.WriteLine(e.Message);
    Console.WriteLine(e.StackTrace);
}

static void HandleParseError(IEnumerable<Error> errs)
{
    errs.Output();
}

static void ConvertFiles(Options args)
{
    var mdFolderPath = ReplaceUnixHomeDir(args.MdFolderPath ?? "");
    var websiteFolderPath = ReplaceUnixHomeDir(args.WebsiteFolder ?? "");
    if (!Directory.Exists(mdFolderPath))
    {
        Console.WriteLine("Markdown folder does not exist at {0}", mdFolderPath);
        return;
    }
    if (!Directory.Exists(websiteFolderPath))
    {
        Console.WriteLine("Website folder does not exist at {0}", websiteFolderPath);
        return;
    }
    var headerFilePath = Path.Combine(websiteFolderPath, "chapter_header.html");
    if (!File.Exists(headerFilePath))
    {
        Console.WriteLine("Header file (header.html) does not exist");
        return;
    }
    var footerFilePath = Path.Combine(websiteFolderPath, "chapter_footer.html");
    if (!File.Exists(footerFilePath))
    {
        Console.WriteLine("Footer file (footer.html) does not exist");
        return;
    }
    var chapterKeyPath = Path.Combine(websiteFolderPath, "metadata", "chapter-key.txt");
    if (!File.Exists(chapterKeyPath))
    {
        Console.WriteLine("Chapter key file (chapter-key.txt) does not exist");
        return;
    }
    // get header text replacements, if any
    Dictionary<string, string> headerTextReplacements = [];
    var headerReplacementPath = Path.Combine(websiteFolderPath, "metadata", "header-replacements.txt");
    if (File.Exists(headerReplacementPath))
    {
        Console.WriteLine("Parsing header replacements...");
        foreach (var line in File.ReadAllLines(headerReplacementPath))
        {
            if (!line.StartsWith('#'))
            {
                var parts = line.Trim().Split(";;;");
                if (parts.Length == 2)
                {
                    headerTextReplacements.Add(parts[0], parts[1]);
                }
            }
        }
    }
    // get chapter number to output file data
    var chapterNumOutputLines = File.ReadAllLines(chapterKeyPath);
    Dictionary<int, string> chapterNumOutputPaths = [];
    var firstChapterNumber = -1;
    var lastChapterNumber = -1;
    foreach (var line in chapterNumOutputLines)
    {
        if (!line.StartsWith('#'))
        {
            var parts = line.Trim().Split("=");
            if (parts.Length != 2)
            {
                Console.WriteLine("Invalid chapter key file; no blank lines and separate chapter # from output path with an = sign");
                return;
            }
            var chapNum = int.Parse(parts[0]);
            chapterNumOutputPaths.Add(chapNum, parts[1]);
            firstChapterNumber = firstChapterNumber == -1 ? chapNum : Math.Min(firstChapterNumber, chapNum);
            lastChapterNumber = lastChapterNumber == -1 ? chapNum : Math.Max(lastChapterNumber, chapNum);
        }
    }
    // find all markdown files and convert to HTML
    // first, grab all metadata and contents
    var paths = Directory.EnumerateFiles(mdFolderPath);
    // chapter number -> metadata dict, chapter text tuple
    Dictionary<int, (Dictionary<string, string>, string)> chapterData = [];
    foreach (var path in paths)
    {
        if (Path.GetExtension(path) != ".md")
        {
            continue; // only parse md files
        }
        Console.WriteLine("Converting {0}...", path);
        // get chapter number
        var digitString = Regex.Match(Path.GetFileName(path), @"\d+").Value;
        var didParse = int.TryParse(digitString, out var chapterNumber);
        if (!didParse)
        {
            Console.WriteLine("Could not find chapter number in path: {0}", path);
            return;
        }

        var contents = File.ReadAllLines(path);
        // strip out metadata and grab actual text content
        var parsingMetadata = false;
        var parsedMetadata = false;
        Dictionary<string, string> metadata = [];
        List<string> chapterContents = [];
        foreach (string line in contents)
        {
            if (line.StartsWith('-'))
            {
                if (parsingMetadata)
                {
                    parsingMetadata = false;
                    parsedMetadata = true;
                }
                else
                {
                    parsingMetadata = true;
                }
                continue;
            }
            if (parsingMetadata)
            {
                var data = line.Trim();
                var index = data.IndexOf(':');
                if (index != -1)
                {
                    var key = data[..index].Trim();
                    var value = data[index..].Trim(':').Trim();
                    metadata.Add(key.Trim(), value);
                }
            }
            else if (parsedMetadata)
            {
                if (!line.Trim().StartsWith("## {")) // these lines are ignorable
                {
                    var outputLine = line;
                    if (line.StartsWith("    "))
                    {
                        outputLine = line[4..];
                    }
                    if (line.Contains("lw{"))
                    {
                        outputLine = Regex.Replace(outputLine, "\\\\lw{(.*?)}", m => $"{m.Groups[1].Value}");
                        outputLine = Regex.Replace(outputLine, "\\\\p{200(.*?)}", m => $"{m.Groups[1].Value}");
                    }
                    chapterContents.Add(outputLine);
                }
            }
        }
        chapterData.Add(chapterNumber, (metadata, string.Join(Environment.NewLine, chapterContents)));
    }
    // actually process every chapter now
    foreach (var chapterDataItem in chapterData)
    {
        var chapterNumber = chapterDataItem.Key;
        var metadata = chapterDataItem.Value.Item1;
        var chapterContents = chapterDataItem.Value.Item2;
        // convert file from markdown to HTML
        var pipeline = new MarkdownPipelineBuilder().UseAdvancedExtensions().Build();
        var chapterHtml = Markdown.ToHtml(string.Join(Environment.NewLine, chapterContents), pipeline);
        chapterHtml = chapterHtml.Replace("h3", "h2");
        // find all egw reference text with format of {AB ##.#} and put into an egw tag
        chapterHtml = Regex.Replace(chapterHtml, "{([A-z]* \\d*.\\d*)}", m => $"<span class=\"egw\">{m.Groups[0].Value}</span>");
        var headerText = File.ReadAllText(headerFilePath);
        foreach (var replace in headerTextReplacements)
        {
            headerText = headerText.Replace(replace.Key, replace.Value);
        }
        // fix header <title> element
        var chapterTitle = metadata["lo"];
        var numberWithLoTitle = chapterNumber > 0 ? $"{chapterNumber}: {chapterTitle}" : $"{chapterTitle}";
        headerText = Regex.Replace(headerText, "<title>(.*?)</title>", $"<title>{numberWithLoTitle}</title>");
        // actually create output now
        var outputFileContents =
            headerText +
            Environment.NewLine +
            $"<h1>{numberWithLoTitle}</h1>";
        if (metadata.TryGetValue("url", out var url))
        {
            outputFileContents += $"<p class=\"chapter-url\"><a target=\"_blank\" href=\"{metadata["url"]}\">{metadata["url"]}</a></p>";
        }
        outputFileContents +=
            chapterHtml +
            Environment.NewLine;
        var linksToPrevNext = "<p class=\"chapter-links\">";
        // Put in links. Assumes everything in same folder or can use full link...
        // not the best, but workable for now.
        var currChapLink = chapterNumOutputPaths[chapterNumber];
        var currChapDirName = Path.GetDirectoryName(currChapLink);
        if (chapterNumber != firstChapterNumber)
        {
            var prevChapNum = chapterNumber - 1;
            var prevChapLink = chapterNumOutputPaths[prevChapNum];
            var prevChapDirName = Path.GetDirectoryName(prevChapLink);
            if (currChapDirName == prevChapDirName)
            {
                prevChapLink = prevChapLink.Replace(currChapDirName + "/", "");
            }
            var prevChapterName = chapterData[prevChapNum].Item1["lo"];
            linksToPrevNext += $"<a class=\"prev-chapter-link\" href=\"{prevChapLink}\">{prevChapNum}: {prevChapterName}</a>";
        }
        if (chapterNumber != lastChapterNumber)
        {
            var nextChapNum = chapterNumber + 1;
            var nextChapLink = chapterNumOutputPaths[nextChapNum];
            var nextChapDirName = Path.GetDirectoryName(nextChapLink);
            if (currChapDirName == nextChapDirName)
            {
                nextChapLink = nextChapLink.Replace(currChapDirName + "/", "");
            }
            var nextChapterName = chapterData[nextChapNum].Item1["lo"];
            linksToPrevNext += $"<a class=\"next-chapter-link\" href=\"{nextChapLink}\">{nextChapNum}: {nextChapterName}</a>";
        }
        outputFileContents += linksToPrevNext;
        outputFileContents += File.ReadAllText(footerFilePath);

        var didHaveChapterNumOutputData = chapterNumOutputPaths.TryGetValue(chapterNumber, out var outputPathStub);
        if (!didHaveChapterNumOutputData || outputPathStub == null)
        {
            Console.WriteLine("Could not find chapter number in key file data: {0}", chapterNumber);
            return;
        }
        var outputFilePath = Path.Combine(websiteFolderPath, outputPathStub);

        File.WriteAllText(outputFilePath, outputFileContents);
    }
}

/// <summary>
/// Checks if a path is a "~/..." unix-path and converts it to an absolute path if it is.
/// </summary>
/// <remarks>
/// This is needed because in C#,
/// "~/foo" is not "/home/users/johndoe/foo"
/// but something like "app/foo".
/// https://stackoverflow.com/a/79582342/3938401
/// </remarks>
static string ReplaceUnixHomeDir(string path)
{
    if (!path.StartsWith('~'))
    {
        return path;
    }
    string userFolder = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    switch (path)
    {
        case "~":
            return userFolder;
        default:
            return Path.Combine(
                userFolder,
                // Substring from the third character to the end: remove "~/" from the start.
                path[2..]
                );
    }
}