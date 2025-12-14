using CommandLine;

public class Options
{
    [Option("md-folder", Required = true, HelpText = "Path to markdown folder with files to convert")]
    public string? MdFolderPath { get; set; }

    [Option("website-folder", Required = true, HelpText = "Path to mwebsite folder with header.html and footer.html")]
    public string? WebsiteFolder { get; set; }
}