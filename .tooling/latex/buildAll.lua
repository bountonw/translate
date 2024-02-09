local function executeShellCommand(command)
    local handle = io.popen(command)
    local result = handle:read("*a")
    handle:close()
    return result
end

local function getDirectories(rootPath)
    local command = string.format("find %s -type d -mindepth 1 -maxdepth 2", rootPath)
    local output = executeShellCommand(command)
    local directories = {}
    for dir in output:gmatch("[^\r\n]+") do
        table.insert(directories, dir)
    end
    return directories
end

local function buildDocumentsForDirectory(directory)
    -- Here, adapt the command to your build process, e.g., calling make with SRCDIR
    local command = string.format("make SRCDIR='%s' build", directory)
    print("Executing: " .. command)
    os.execute(command)
end

local function main()
    local thDirectories = getDirectories("../../th")
    local loDirectories = getDirectories("../../lo")

    -- Build documents for Thai directories
    for _, dir in ipairs(thDirectories) do
        buildDocumentsForDirectory(dir)
    end

    -- Build documents for Lao directories
    for _, dir in ipairs(loDirectories) do
        buildDocumentsForDirectory(dir)
    end
end

main()
