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

static string RemoveLwAndPTagsInText(string txt)
{
    if (string.IsNullOrWhiteSpace(txt))
    {
        return "";
    }
    // remove \p{} first, since it can sit inside \lw{}, e.g. \lw{ເລັກ\p{200}ນ້ອຍ}
    txt = Regex.Replace(txt, "\\\\p{(-?.*?)}", m => $"");
    txt = Regex.Replace(txt, "\\\\lw{(.*?)}", m => $"{m.Groups[1].Value}");
    txt = Regex.Replace(txt, "\\\\GCcode{(.*?)}", m => $"{m.Groups[1].Value}");
    txt = txt.Replace("\\newpage", "");
    // escape bracketed text right before a footnote ref, e.g. [ຈາກນັ້ນ...][^16],
    // or markdown reads it as a link to the footnote and drops the text
    txt = Regex.Replace(txt, "\\[([^\\[\\]^][^\\[\\]]*)\\](?=\\[\\^)", m => $"\\[{m.Groups[1].Value}\\]");
    txt = txt.Replace("\\s", "");
    txt = txt.Replace("\\S", "");
    return txt;
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
            // only the two --- lines that open and close the front matter
            if (!parsedMetadata && line.Trim() == "---")
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
                if (!line.Trim().StartsWith("## {")) // paragraph tags like ## {GC 17.1} are navigation only
                {
                    var outputLine = line;
                    if (line.StartsWith("    "))
                    {
                        outputLine = line[4..];
                    }
                    // with the ## tags stripped, ### subheadings become second level
                    outputLine = Regex.Replace(outputLine, "^#(#{2,}) ", "$1 ");
                    outputLine = RemoveLwAndPTagsInText(outputLine);
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
        // replace special chars in chapter markdown/latex contents
        chapterContents = chapterContents.Replace("{\\;}", " ").Replace("{\\:}", " ");
        // convert file from markdown to HTML
        // no list extras: they read initials such as "W. H. D." as a lettered list;
        // no auto identifiers: Lao headings all come out as "section", "section-1"...
        var pipelineBuilder = new MarkdownPipelineBuilder().UseAdvancedExtensions();
        pipelineBuilder.Extensions.RemoveAll(e =>
            e is Markdig.Extensions.ListExtras.ListExtraExtension ||
            e is Markdig.Extensions.AutoIdentifiers.AutoIdentifierExtension);
        var pipeline = pipelineBuilder.Build();
        var chapterHtml = Markdown.ToHtml(string.Join(Environment.NewLine, chapterContents), pipeline);
        // find all egw reference text with format of {AB ##.#} and put into an egw tag
        chapterHtml = Regex.Replace(chapterHtml, "{([A-z]* \\d*.\\d*)}", m => $"<span class=\"egw\">{m.Groups[0].Value}</span>");
        // a reference ending a paragraph names that paragraph, so it can be linked
        // as chapters/01_xxx.html#GC17.1; the reference itself links there
        chapterHtml = Regex.Replace(
            chapterHtml,
            "<p>((?:(?!</?p>).)*?)<span class=\"egw\">{([A-Za-z]+) (\\d+\\.\\d+)}</span></p>",
            m =>
            {
                var id = m.Groups[2].Value + m.Groups[3].Value;
                return $"<p id=\"{id}\">{m.Groups[1].Value}<span class=\"egw\"><a href=\"#{id}\">{{{m.Groups[2].Value} {m.Groups[3].Value}}}</a></span></p>";
            },
            RegexOptions.Singleline);
        // find any remaining \emph tags and put it in <em></em> tags
        chapterHtml = Regex.Replace(chapterHtml, "\\\\emph{(.*?)}", m => $"<em>{m.Groups[1].Value}</em>");
        chapterHtml = Regex.Replace(chapterHtml, "\\\\thai{(.*?)}", m => $"<span lang=\"th\" class=\"thai\">{m.Groups[1].Value}</span>");
        // fix nbsp tags
        chapterHtml = chapterHtml.Replace("\\nbsp", "&nbsp;");
        var headerText = File.ReadAllText(headerFilePath);
        foreach (var replace in headerTextReplacements)
        {
            headerText = headerText.Replace(replace.Key, replace.Value);
        }
        // fix header <title> element
        var numberWithLoTitle = NumberedTitle(chapterNumber, metadata["lo"]);
        headerText = Regex.Replace(
            headerText,
            "<title>(.*?)</title>",
            $"<title>{numberWithLoTitle}</title>{Environment.NewLine}    <meta property=\"og:title\" content=\"{numberWithLoTitle}\">");
        // actually create output now
        var outputFileContents =
            headerText +
            Environment.NewLine +
            $"<h1>{numberWithLoTitle}</h1>";
        if (metadata.TryGetValue("url", out var url))
        {
            outputFileContents += $"<p class=\"chapter-url\"><a target=\"_blank\" href=\"{url}\">ຕົ້ນສະບັບພາສາອັງກິດ</a></p>";
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
            var prevChapterName = NumberedTitle(prevChapNum, chapterData[prevChapNum].Item1["lo"]);
            linksToPrevNext += $"<a class=\"prev-chapter-link\" href=\"{prevChapLink}\">{prevChapterName}</a>";
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
            var nextChapterName = NumberedTitle(nextChapNum, chapterData[nextChapNum].Item1["lo"]);
            linksToPrevNext += $"<a class=\"next-chapter-link\" href=\"{nextChapLink}\">{nextChapterName}</a>";
        }
        outputFileContents += linksToPrevNext + "</p>" + Environment.NewLine;
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
    // rewrite the contents list in index.html from the chapter titles,
    // so the contents page always matches the chapters
    var indexPath = Path.Combine(websiteFolderPath, "index.html");
    if (!File.Exists(indexPath))
    {
        Console.WriteLine("No index.html; contents page not written");
        return;
    }
    var indexText = File.ReadAllText(indexPath);
    var tocMatch = Regex.Match(indexText, "(<nav class=\"toc\">\\s*<ol>)(.*?)(\\s*</ol>)", RegexOptions.Singleline);
    if (!tocMatch.Success)
    {
        Console.WriteLine("No <nav class=\"toc\"><ol> in index.html; contents page not written");
        return;
    }
    var tocItems = "";
    foreach (var chapNum in chapterNumOutputPaths.Keys.Order())
    {
        if (!chapterData.TryGetValue(chapNum, out var chapter))
        {
            continue;
        }
        tocItems += Environment.NewLine +
            "            <li>" + Environment.NewLine +
            $"                <a href=\"{chapterNumOutputPaths[chapNum]}\">{NumberedTitle(chapNum, chapter.Item1["lo"])}</a>" + Environment.NewLine +
            "            </li>";
    }
    indexText = indexText[..tocMatch.Groups[2].Index] + tocItems + indexText[(tocMatch.Groups[2].Index + tocMatch.Groups[2].Length)..];
    File.WriteAllText(indexPath, indexText);
}

/// <summary>
/// "1. Title" as on the printed contents page; the introduction (0) has no number.
/// </summary>
static string NumberedTitle(int chapterNumber, string title)
{
    title = RemoveLwAndPTagsInText(title);
    return chapterNumber > 0 ? $"{chapterNumber}. {title}" : title;
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