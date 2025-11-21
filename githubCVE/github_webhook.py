# webhook_listener.py
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
import hmac
import hashlib
import json
import asyncio
import os
from typing import Optional
import sys
sys.path.append('..')
from github_mcp_cve import GitHubMCPAgent

app = FastAPI()
from dotenv import load_dotenv
load_dotenv()

# Configuration
WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "").encode()
BOT_USERNAME = os.environ.get("BOT_USERNAME", "prasadrg98")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify webhook signature"""
    if not signature_header:
        return False
    
    hash_object = hmac.new(
        WEBHOOK_SECRET, 
        msg=payload_body, 
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)

def is_our_pr(payload: dict) -> bool:
    """
    Check if the PR was created by our bot/user
    This filters out all other PRs
    """
    # pr_author = payload.get("pull_request", {}).get("user", {}).get("login", "")
    title = payload.get("pull_request", {}).get("title", "")
    return "AutomatedPR" in title

def extract_domain_owner_repo_from_github_input(input_str: str) -> tuple[str, str, str]:
    """
    Extract domain, owner, repo from various GitHub input formats (github.com, github-cisco.com, etc)
    Supported formats:
    - owner/repo
    - https://github.com/owner/repo
    - https://github-cisco.com/owner/repo.git
    - https://github5.com/owner/repo/pulls
    - git@github.com:owner/repo.git
    - git@github-cisco.com:owner/repo.git
    Returns:
        tuple[str, str, str]: (domain, owner, repo)
    Raises:
        ValueError: If the input format is not recognized or invalid
    """
    if not input_str:
        raise ValueError("Input cannot be empty")
    input_str = input_str.strip()

    # SSH format: git@domain:owner/repo.git
    if input_str.startswith("git@"):
        ssh_part = input_str.replace("git@", "")
        domain, rest = ssh_part.split(":", 1)
        if rest.endswith(".git"):
            rest = rest[:-4]
        parts = rest.split("/")
        if len(parts) >= 2:
            return domain, parts[0], parts[1]
        raise ValueError(f"Invalid SSH GitHub URL format: {input_str}")

    # HTTPS/HTTP format: https://domain/owner/repo...
    if input_str.startswith("http://") or input_str.startswith("https://"):
        url = input_str.split("//", 1)[1]
        domain_and_path = url.split("/", 1)
        domain = domain_and_path[0]
        path = domain_and_path[1] if len(domain_and_path) > 1 else ""
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1]
            return domain, owner, repo
        raise ValueError(f"Invalid GitHub URL format: {input_str}")

    # owner/repo or owner/repo/extra
    if "/" in input_str:
        parts = input_str.split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1]
            # Default domain if not specified
            return "github.com", owner, repo
        raise ValueError(f"Invalid owner/repo format: {input_str}")
    
    raise ValueError(f"Unrecognized format: {input_str}. Expected 'owner/repo' or GitHub URL")

@app.post("/dependency-upgrade")
async def dependency_upgrade(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint to trigger dependency upgrade
    Expected payload:
    {
        "repo_full_url": "owner/repo",
        "dependency_name": "apacheHTTPClientVersion", 
        "new_version": "4.5.15"
    }
    """
    payload = await request.json()
    print(f"Received dependency upgrade request: {json.dumps(payload)}")

    # Step 1: Extract and validate required parameters
    repo_full_url = payload.get("repo_full_url", "").strip()
    dependency_name = payload.get("dependency_name", "").strip()
    new_version = payload.get("new_version", "").strip()

    # Validate not empty
    if not repo_full_url:
        raise HTTPException(status_code=400, detail="repo_full_url is required and cannot be empty")
    if not dependency_name:
        raise HTTPException(status_code=400, detail="dependency_name is required and cannot be empty")
    if not new_version:
        raise HTTPException(status_code=400, detail="new_version is required and cannot be empty")
    
    # Extract domain, owner, repo from various GitHub URL formats or owner/repo format
    try:
        domain, owner, repo = extract_domain_owner_repo_from_github_input(repo_full_url)
        if not domain or not owner or not repo:
            raise ValueError("Invalid format")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid repo_full_url format: {str(e)}. Expected 'owner/repo' or GitHub URL")

    print(f"✓ Validated params - Domain: {domain}, Repo: {owner}/{repo}, Dependency: {dependency_name}, Version: {new_version}")

    # Step 2: Initialize agent and execute workflow
    agent = GitHubMCPAgent(
        github_token=GITHUB_TOKEN,
        domain=domain,
        repo_owner=owner,
        repo_name=repo,
        repo_url=repo_full_url
    )
    
    try:
        await agent.initialize()
        
        # Step 3: Update gradle and create PR
        pr_number = await agent.update_gradle_version_workflow(dependency_name, new_version)
        
        if pr_number:
            print(f"✓ Successfully created PR #{pr_number}")
            return {
                "status": "success", 
                "pr_number": pr_number,
                "repo": repo_full_url,
                "dependency": dependency_name,
                "version": new_version
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create PR - no PR number returned")
            
    except Exception as e:
        print(f"✗ Failed to create PR for {dependency_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create PR: {str(e)}")
    finally:
        await agent.cleanup()


@app.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Webhook endpoint - receives ALL GitHub events but filters for our PRs only
    """
    payload_body = await request.body()
    
    # # Verify signature
    # if not verify_signature(payload_body, x_hub_signature_256):
    #     raise HTTPException(status_code=403, detail="Invalid signature")
    
    payload = json.loads(payload_body.decode("utf-8"))
    print(f"Received event: {x_github_event}, action: {payload.get('action')}")
    # print(f"payload: {json.dumps(payload)}")
    
    # Filter: Only process pull_request_review events
    if x_github_event == "pull_request_review":
        # Check if this PR was created by our bot
        if not is_our_pr(payload):
            print(f"Ignoring review event - PR not created by {BOT_USERNAME}")
            return {"status": "ignored", "reason": "not our PR"}
        
        action = payload.get("action")
        review_state = payload.get("review", {}).get("state")
        
        # Check if approved
        if action == "submitted" and review_state == "approved":
            pr_number = payload["pull_request"]["number"]
            repo_full_name = payload["repository"]["full_name"]
            
            print(f"✓ Our PR #{pr_number} was approved!")
            
            # Trigger agentic workflow in background
            background_tasks.add_task(
                handle_pr_approval,
                repo_full_name,
                pr_number
            )
    
    # Filter: Only process merged PRs created by us
    elif x_github_event == "pull_request":
        if not is_our_pr(payload):
            print(f"Ignoring PR event - not created by {BOT_USERNAME}")
            return {"status": "ignored", "reason": "not our PR"}
        
        action = payload.get("action")
        
        if action == "closed" and payload["pull_request"].get("merged"):
            pr_number = payload["pull_request"]["number"]
            repo_full_name = payload["repository"]["full_name"]
            merge_commit_sha = payload["pull_request"].get("merge_commit_sha")

            print(f"✓ Our PR #{pr_number} was merged! Repo: {repo_full_name}, Commit: {merge_commit_sha}")

            # # Trigger release workflow
            background_tasks.add_task(
                handle_pr_merged,
                repo_full_name,
                pr_number,
                merge_commit_sha
            )
    
    return {"status": "success"}

async def handle_pr_approval(repo_full_name: str, pr_number: int):
    """
    Handle approval of OUR PR - trigger agent to merge
    """
    print(f"Processing approval for our PR #{pr_number} in {repo_full_name}")

    domain, owner, repo = extract_domain_owner_repo_from_github_input(repo_full_name)
    agent = GitHubMCPAgent(
        github_token=GITHUB_TOKEN,
        domain=domain,
        repo_owner=owner,
        repo_name=repo,
        repo_url=repo_full_name
    )

    can_be_merged = agent.is_pr_can_be_merged(pr_number)
    if not can_be_merged:
        print(f"PR #{pr_number} is not ready to be merged yet.")
        return

    print(f"Merging PR #{pr_number}...")
    try:
        await agent.initialize()
        await agent.merge_pr(pr_number)
        print(f"✓ PR #{pr_number} merged successfully.")
    except Exception as e:
        print(f"✗ Failed to merge PR #{pr_number}: {e}")
    finally:
        await agent.cleanup()


def handle_pr_merged(repo_full_name: str, pr_number: int, merge_commit_sha: str):
    """
    Handle merge of OUR PR - trigger agent to create release
    """
    print(f"Creating release for merged PR #{pr_number} in {repo_full_name}")
    
    domain, owner, repo = extract_domain_owner_repo_from_github_input(repo_full_name)
    agent = GitHubMCPAgent(
        github_token=GITHUB_TOKEN,
        domain=domain,
        repo_owner=owner,
        repo_name=repo,
        repo_url=repo_full_name
    )
    
    try:
        # Use direct create_release method (no additional initialization needed)
        result = agent.create_release(merge_commit_sha, pr_number)
        print(f"✓ Release created for PR #{pr_number} with tag: {result['tag_name']}")
    except Exception as e:
        print(f"✗ Failed to create release for PR #{pr_number}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
