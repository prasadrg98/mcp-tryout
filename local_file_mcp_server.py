from fastmcp import FastMCP
import os
import sys

if len(sys.argv) > 1:
    base_path = sys.argv[1]
    print(f"Using provided base path: {base_path}")
else:
    print("No base path provided, using default ~/Desktop/educosys")
    base_path = os.path.expanduser("~/Desktop/educosys")

mcp = FastMCP("localfilesystem")


@mcp.tool()
def add_file(filename: str, content: str = "This is a new file created by MCP server."):
    """Create a new file with some default content in current directory"""
    filepath = os.path.join(base_path, filename)
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(content)
        return f"File {filename} created."
    else:
        return f"File {filename} already exists."

@mcp.tool()
def add_folder(foldername: str):
    """Create a new folder in current directory"""
    folderpath = os.path.join(base_path, foldername)
    if not os.path.exists(folderpath):
        os.makedirs(folderpath)
        return f"Folder {foldername} created."
    else:
        return f"Folder {foldername} already exists."

@mcp.tool()
def remove_file(filename: str):
    """Remove a file in current directory"""
    filepath = os.path.join(base_path, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return f"File {filename} removed."
    else:
        return f"File {filename} does not exist."

@mcp.tool()
def list_files():
    """List all files and folders in current directory"""
    items = os.listdir(base_path)
    if items:
        return "Files and folders:\n" + "\n".join(items)
    else:
        return "No files or folders found."

@mcp.tool()
def read_file(filename: str):
    """Read content of a file in current directory"""
    filepath = os.path.join(base_path, filename)
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read()
        return f"Content of {filename}:\n{content}"
    else:
        return f"File {filename} does not exist."

if __name__ == "__main__":
    mcp.run(transport="stdio")