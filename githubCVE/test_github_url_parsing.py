#!/usr/bin/env python3
"""
Test script for GitHub URL parsing functionality
"""

import sys

def extract_owner_repo_from_github_input(input_str: str) -> tuple[str, str]:
    """
    Extract owner and repo from various GitHub input formats:
    
    Supported formats:
    - owner/repo
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo/pulls
    - https://github.com/owner/repo/issues/123
    - https://github.com/owner/repo/tree/main/src
    - git@github.com:owner/repo.git
    
    Returns:
        tuple[str, str]: (owner, repo)
    
    Raises:
        ValueError: If the input format is not recognized or invalid
    """
    if not input_str:
        raise ValueError("Input cannot be empty")
    
    input_str = input_str.strip()
    
    # Handle SSH format: git@github.com:owner/repo.git
    if input_str.startswith("git@github.com:"):
        ssh_part = input_str.replace("git@github.com:", "")
        # Remove .git suffix if present
        if ssh_part.endswith(".git"):
            ssh_part = ssh_part[:-4]
        parts = ssh_part.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
        raise ValueError(f"Invalid SSH GitHub URL format: {input_str}")
    
    # Handle HTTPS URLs: https://github.com/owner/repo/*
    if input_str.startswith(("https://github.com/", "http://github.com/")):
        # Remove protocol and domain
        path_part = input_str.replace("https://github.com/", "").replace("http://github.com/", "")
        
        # Remove .git suffix if present
        if path_part.endswith(".git"):
            path_part = path_part[:-4]
        
        # Split by / and take first two parts (owner/repo)
        parts = path_part.split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1]
            if owner and repo:
                return owner, repo
        
        raise ValueError(f"Invalid GitHub URL format: {input_str}")
    
    # Handle simple owner/repo format
    if "/" in input_str:
        # Split only on first slash to handle cases like owner/repo/path
        parts = input_str.split("/", 1)
        if len(parts) == 2:
            owner = parts[0]
            # Take only the repo name (before any additional path)
            repo_with_path = parts[1]
            repo = repo_with_path.split("/")[0]  # Get just the repo name
            
            if owner and repo:
                return owner, repo
        
        raise ValueError(f"Invalid owner/repo format: {input_str}")
    
    raise ValueError(f"Unrecognized format: {input_str}. Expected 'owner/repo' or GitHub URL")

def test_github_url_parsing():
    """Test various GitHub URL formats"""
    test_cases = [
        # Standard formats
        ("owner/repo", ("owner", "repo")),
        ("microsoft/vscode", ("microsoft", "vscode")),
        
        # HTTPS URLs
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/microsoft/vscode", ("microsoft", "vscode")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        
        # URLs with paths
        ("https://github.com/owner/repo/pulls", ("owner", "repo")),
        ("https://github.com/owner/repo/issues/123", ("owner", "repo")),
        ("https://github.com/owner/repo/tree/main/src", ("owner", "repo")),
        ("https://github.com/microsoft/vscode/blob/main/README.md", ("microsoft", "vscode")),
        
        # SSH format
        ("git@github.com:owner/repo.git", ("owner", "repo")),
        ("git@github.com:microsoft/vscode.git", ("microsoft", "vscode")),
        
        # With additional paths in owner/repo format
        ("owner/repo/some/path", ("owner", "repo")),
        
        # HTTP (non-secure)
        ("http://github.com/owner/repo", ("owner", "repo")),
    ]
    
    failed = 0
    passed = 0
    
    print("🧪 Testing GitHub URL parsing...")
    print("=" * 50)
    
    for input_str, expected in test_cases:
        try:
            result = extract_owner_repo_from_github_input(input_str)
            if result == expected:
                print(f"✅ {input_str:50} → {result}")
                passed += 1
            else:
                print(f"❌ {input_str:50} → {result} (expected {expected})")
                failed += 1
        except Exception as e:
            print(f"💥 {input_str:50} → ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    # Test error cases
    print("\n🚨 Testing error cases...")
    error_cases = [
        "",
        "invalid",
        "no-slash",
        "https://gitlab.com/owner/repo",  # Wrong domain
        "/just/slash",
        "owner/",
        "/repo",
    ]
    
    for input_str in error_cases:
        try:
            result = extract_owner_repo_from_github_input(input_str)
            print(f"⚠️  {input_str:30} → {result} (should have failed)")
        except ValueError as e:
            print(f"✅ {input_str:30} → ERROR: {e}")
        except Exception as e:
            print(f"💥 {input_str:30} → UNEXPECTED ERROR: {e}")
    
    return failed == 0

if __name__ == "__main__":
    success = test_github_url_parsing()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    sys.exit(0 if success else 1)