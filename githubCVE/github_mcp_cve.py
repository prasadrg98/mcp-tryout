# agent_workflow.py
import asyncio
import logging
import pkgutil
from xmlrpc import client
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()

for module_info in pkgutil.iter_modules():
    # print("Disabling logs for module:", module_info.name)
    logging.getLogger(module_info.name).setLevel(logging.ERROR)

class GitHubMCPAgent:
    """
    Agentic workflow that uses GitHub MCP for all operations
    """
    
    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.repo_full_name = f"{repo_owner}/{repo_name}"
        self.client = None
        self.agent = None
        
    async def initialize(self):
        """Initialize the MCP client and agent"""
        # Configure GitHub MCP Server
        self.client = MultiServerMCPClient({
            "github": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-github"
                ],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token
                },
               "transport": "stdio"
            }
        })
        llm = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
        tools = await self.client.get_tools()
        self.agent = create_react_agent(llm, tools)
        
    async def cleanup(self):
        """Cleanup MCP client"""
        if self.client:
            try:
                # For MultiServerMCPClient, we need to properly close all sessions
                if hasattr(self.client, 'close_all'):
                    await self.client.close_all()
                elif hasattr(self.client, '_sessions'):
                    # Manually close each session
                    for session_name, session in self.client._sessions.items():
                        try:
                            if hasattr(session, 'close'):
                                await session.close()
                        except Exception as session_e:
                            print(f"Warning: Error closing session {session_name}: {session_e}")
                # Set to None for garbage collection
                self.client = None
                print("✓ MCP client cleaned up successfully")
            except Exception as e:
                print(f"Warning: Error during client cleanup: {e}")
                self.client = None

    def is_pr_can_be_merged(self, pr_number: int) -> bool:
        """
        Check if PR can be merged - uses direct GitHub API as fallback
        """

        # Try direct GitHub API call first since MCP server doesn't return mergeable fields
        print("Trying direct GitHub API call...")
        url = f"https://api.github.com/repos/{self.repo_full_name}/pulls/{pr_number}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            print(f"Direct API Response mergeable_state: {data.get('mergeable_state')}")

            # Check mergeable_state first
            mergeable_state = data.get('mergeable_state')
            if mergeable_state:
                if mergeable_state == 'clean':
                    print(f"PR mergeable_state is {mergeable_state}, can be merged.")
                    return True
                print(f"PR mergeable_state is {mergeable_state}, cannot be merged.")
                return False

        except Exception as e:
            print(f"Error calling GitHub API directly: {e}")
        return False

    async def update_gradle_version_workflow(self, dependency_name: str, new_version: str):
        """
        Complete workflow: Update gradle file -> Create PR
        Agent decides how to accomplish this using available MCP tools
        # Update the version for dependency "{dependency_name}" to {new_version}
        #    Search for and update these specific patterns in the gradle files:
        #    - {dependency_name}Version = "{new_version}" (camelCase variable)
        #    - {dependency_name}_version = "{new_version}" (snake_case variable)
        #    - {dependency_name}-version = "{new_version}" (kebab-case variable)
        #    - ext.{dependency_name}Version = "{new_version}" (ext property)
        #    - ext.{dependency_name} = "{new_version}" (short ext property)
        #    - def {dependency_name}Version = "{new_version}" (def variable)
        #    - In gradle.properties: {dependency_name}.version={new_version}
        #    - In version catalog: {dependency_name} = "{new_version}"
        #    - Direct dependency: '{dependency_name}:{new_version}' (if group:artifact pattern)
        #    - Implementation dependency: implementation '{dependency_name}:{new_version}'
        """

        if not dependency_name or not dependency_name.strip() or not new_version or not new_version.strip():
            raise ValueError("Both dependency_name and new_version must be provided for version update workflow.")

        prompt = f"""
        I need you to update a Gradle project version and create a pull request.

        Repository: {self.repo_full_name}
        New version: {new_version}
        Dependency: {dependency_name}

        Please follow these steps:
        1. First, list all files in the repository root to see what gradle-related files exist
        2. Look for files containing "gradle" in the filenames (it might be named something like "*.gradle" or similar)
        3. Once you find the gradle files,
         3.1 For each file, get its content from the master branch
        4. Find the line containing: {dependency_name}
        5. IMPORTANT: When updating the file, create a new branch FIRST before making any file changes
           Branch name: "update-{dependency_name}-{new_version}"
        6. Update ONLY the specific line with {dependency_name} to use version "{new_version}"
           Keep all other content exactly the same - do not modify any other dependencies
        7. Commit the updated file with message "Update {dependency_name} to {new_version} - Automated"
        8. Create a pull request from the new branch to master with:
           - Title: "Update {dependency_name} to {new_version} - AutomatedPR"
           - Body: "Automated {dependency_name} update to {new_version}"
        8. Return the PR number when done

        Please execute this workflow and let me know the PR number in #PR<PR_NUMBER> when complete.
        """
        
        # Run the agent
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        })
        
        print("Agent response:", result)
        # Extract PR number from agent's response
        pr_number = self._extract_pr_number(result)
        
        return pr_number
    
    async def merge_pr(self, pr_number: int):
        """
        Merge a pull request
        """
        
        prompt = f"""
        Merge pull request #{pr_number} in repository {self.repo_full_name}.
        
        Use squash merge method and return the merge commit SHA.
        """
        
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        })
        
        return result
    
    def create_release(self, merge_commit_sha: str, pr_number: int):
        """
        Create a GitHub release using direct API call
        """
        
        version_tag = f"auto-pr-{pr_number}"
        
        url = f"https://api.github.com/repos/{self.repo_full_name}/releases"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        release_data = {
            "tag_name": version_tag,
            "target_commitish": merge_commit_sha,
            "name": f"Release {version_tag}",
            "body": f"release {version_tag} from PR #{pr_number}",
            "draft": False,
            "prerelease": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=release_data)
            response.raise_for_status()
            data = response.json()
            print(f"✅ Created release: {data['tag_name']} - {data['html_url']}")
            return data
            
        except Exception as e:
            print(f"Error creating release: {e}")
            return None

    async def merge_and_release_workflow(self, pr_number: int):
        """
        Merge PR and create release with automatic version management
        """
        
        prompt = f"""
        I need you to merge a pull request and create a release with automatic version increment.
        
        Repository: {self.repo_full_name}
        PR Number: {pr_number}
        
        Please follow these steps:
        1. Merge the pull request using squash merge
        2. Get the merge commit SHA
        3. Check existing tags/releases to determine the next version:
           - If no tags exist, use v1.0.0
           - If tags exist, find the highest version and increment patch number (e.g., v1.2.3 -> v1.2.4)
        4. Create a git tag with the new version on the merge commit
        5. Create a GitHub release with:
           - Tag: v<next_version>
           - Name: Release v<next_version>
           - Body: "Automated release v<next_version> from PR #{pr_number}"
        
        Please execute this workflow and confirm when the release is created with the version number.
        """
        
        result = await self.agent.ainvoke({
            "messages": [HumanMessage(content=prompt)]
        })
        
        return result

    def _extract_commit_sha(self, agent_result):
        """Extract commit SHA from agent response"""
        # Parse the agent's final response
        messages = agent_result.get("messages", [])
        final_message = messages[-1].content if messages else ""
        
        # Look for commit SHA patterns (40 character hex string)
        import re
        # GitHub commit SHA is 40 characters of hex
        match = re.search(r'\b([a-f0-9]{40})\b', final_message, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Alternative: look for "commit" followed by SHA
        match = re.search(r'commit[:\s]+([a-f0-9]{40})', final_message, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: look for "sha" followed by the hash
        match = re.search(r'sha[:\s]+([a-f0-9]{40})', final_message, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None

    def _extract_pr_number(self, agent_result):
        """Extract PR number from agent response"""
        # Parse the agent's final response
        messages = agent_result.get("messages", [])
        final_message = messages[-1].content if messages else ""
        
        # Simple pattern matching (enhance as needed)
        import re
        match = re.search(r'PR\s*#?(\d+)', final_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Alternative: look for "pull request number" or similar
        match = re.search(r'(?:pull request|PR)\s+(?:number\s+)?(\d+)', final_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        return None


async def run_version_update(dependency_name: str, new_version: str):
    """Run the complete version update workflow"""
    agent = GitHubMCPAgent(
        github_token=os.getenv("GITHUB_TOKEN"),
        repo_owner="prasadrg98",
        repo_name="sample"
    )
    
    await agent.initialize()
    
    # Step 1 & 2: Update gradle and create PR
    pr_number = await agent.update_gradle_version_workflow(dependency_name, new_version)
    if pr_number:
        print(f"Created PR #{pr_number}")
    else:
        print("PR not have been created.")
        raise RuntimeError("Failed to create PR, stopping workflow.")
    return pr_number

async def merge_pr_and_get_release(pr_number: int):
    """Run the complete split workflow in a single async context"""
    
    agent = GitHubMCPAgent(
        github_token=os.getenv("GITHUB_TOKEN"),
        repo_owner="prasadrg98", 
        repo_name="sample"
    )

    # Initialize the agent first
    await agent.initialize()

    # Step 1: Check if PR can be merged (using sync method)
    # pr_number = 3
    can_merge = agent.is_pr_can_be_merged(pr_number)
    print(f"Can PR #{pr_number} be merged: {can_merge}")
    
    if not can_merge:
        print("❌ PR is NOT ready to merge - stopping workflow")
        raise RuntimeError("PR cannot be merged, stopping workflow.")

    # Step 2: Merge the PR
    print(f"✅ PR #{pr_number} is ready to merge - proceeding...")
    merge_pr_result = await agent.merge_pr(pr_number)
    print(f"Merge PR result: {merge_pr_result}")
    
    # Step 3: Extract commit SHA from merge result
    commit_sha = agent._extract_commit_sha(merge_pr_result)
    print(f"Extracted commit SHA: {commit_sha}")

    # Step 4: Create release with extracted commit SHA
    if commit_sha:
        release_result = agent.create_release(commit_sha, pr_number)
        print(f"Release result: {release_result}")
        print("✅ Workflow completed successfully!")
    else:
        print("❌ Could not extract commit SHA, skipping release creation")

# To run the example (uncomment below lines)
if __name__ == "__main__":
    try:
        # The agent will be initialized inside merge_pr_and_get_release
        # asyncio.run(merge_pr_and_get_release())
        pr_number = asyncio.run(run_version_update("kotlin", "4.5.16"))
        print(f"Version update result: PR{pr_number}")
        # Proceed with merging the PR and creating a release

    finally:
        print("Cleaning up...")

    
