import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 


async def get_github_repo_files(repo_path: str):
    """Get files from GitHub repository using direct API call"""
    if not GITHUB_TOKEN:
        return "Error: GitHub token not found"
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{repo_path}/contents",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    files = []
                    for item in data:
                        files.append(f"{item['name']} ({item['type']})")
                    return f"Files in {repo_path}:\n" + "\n".join(files)
                else:
                    error_text = await response.text()
                    return f"GitHub API error {response.status}: {error_text}"
    except Exception as e:
        return f"Error: {str(e)}"

async def main():
    print("Testing direct GitHub API integration...")
    
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not found in .env file")
        return
    
    print(f"Using GitHub token: {GITHUB_TOKEN[:10]}...")
    
    # Test GitHub API directly
    repo_info = await get_github_repo_files("prasadrg98/sample")
    print("\nGitHub Repository Contents:")
    print("=" * 50)
    print(repo_info)
    
    # Test with your other repo
    repo_info2 = await get_github_repo_files("rgrg/EducosysGenerativeAI")
    print("\nEducosys Repository Contents:")
    print("=" * 50) 
    print(repo_info2)

if __name__ == "__main__":
    asyncio.run(main())
