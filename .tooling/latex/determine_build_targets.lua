--[[ Script Name: determine_build_targets.lua

    Description: 
    This Lua script is designed to facilitate a dynamic build process by
    analyzing git changes to identify the scope of document generation
    required. It checks for changes in three key areas: 
    - 1. The '/latex/' directory, which contains shared resources for
      document generation.  Changes here trigger a global build process,
      affecting all Thai and Lao *.md documents.  
    - 2. The 'th/' and 'lo/' directories, which are organized by
      language and contain individual books or booklets.  Changes within
      these directories trigger builds at the book or booklet level.
      The script outputs identifiers for the affected documents (global,
      specific languages, or specific books/booklets) based on the
      changes detected, enabling conditional builds in a GitHub Actions
      workflow or local environment.

    Assumptions:
    - The script runs in an environment where the current working
      directory is the root of a Git repository, with Lua and Git
      installed.
    - The repository structure includes a 'latex/' directory for shared
      resources and 'th/' and 'lo/' directories for language-specific
      content, further organized into books or booklets.
    - The build process is triggered by modifications to Markdown files
      (.md) or relevant changes in the 'latex/' directory.

    Usage:
    - Execute the script as part of a CI/CD pipeline (e.g., GitHub
      Actions) or locally to determine build targets dynamically.  The
      output guides the subsequent build process, ensuring only the
      necessary documents are generated or updated based on the latest
      changes.  ]]


--[[ Script Description Here ]]

local function executeShellCommand(command)
    local handle = io.popen(command)
    local result = handle:read("*a")
    handle:close()
    return result
end

local function valueExistsInTable(tbl, value)
    for _, v in pairs(tbl) do
        if v == value then
            return true
        end
    end
    return false
end

local translationStatusDirs = {"01_raw", "02_edit", "03_public"}

-- Get changed files from git
local changedFiles = executeShellCommand("git diff --name-only HEAD~1")
local changesTriggerGlobalBuild = false

for line in changedFiles:gmatch("[^\r\n]+") do
    if line:match("^latex/") then
        changesTriggerGlobalBuild = true
        break  -- No need to check further if global build is triggered
    end

    local filePathSegments = {}
    for segment in string.gmatch(line, "[^/]+") do
        table.insert(filePathSegments, segment)
    end

    if #segments > 0 and (segments[1] == "th" or segments[1] == "lo") and valueExistsInTable(translationStatusDirs, segments[#segments-2]) then
        local langCode = segments[#segments]:match("_(%w+)%.md$")
        local bookOrBooklet = #segments >= 5 and segments[#segments-3] or segments[#segments-3]
        local currentTime = os.date("!%Y%m%d_%H%M%S")
        local artifactName = string.format("%s_%s_%s", bookOrBooklet, langCode, currentTime)

        print("Artifact name: ", artifactName)
    end
end

if changesTriggerGlobalBuild then
    -- Handle the global build trigger
    local currentTime = os.date("!%Y%m%d_%H%M%S")
    print("Global build triggered for all documents at time: ", currentTime)
end
