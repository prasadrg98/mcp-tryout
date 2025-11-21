#!/usr/bin/env python3
"""
Comprehensive test script for Dependency Analysis Service
Tests multiple repositories and scenarios
"""

import requests
import json
import time
import os
import sys

# Allow configuring service URL via environment variable
SERVICE_URL = os.environ.get("SERVICE_URL", "http://localhost:5003")

def test_health_check():
    """Test health check endpoint"""
    print(f"🔍 Testing health check against {SERVICE_URL}...")
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=5)
        print(f"Health Check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        return False

def run_analysis_test(repo, dependency, description):
    """Run a single analysis test"""
    print(f"\n🚀 {description}")
    print(f"Repository: {repo}")
    print(f"Dependency: {dependency}")
    
    request_data = {
        "repository": repo,
        "dependency_name": dependency,
    }
    
    try:
        response = requests.post(f"{SERVICE_URL}/analyze", json=request_data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        return False

    if response.status_code != 200:
        print(f"❌ Analysis request failed: {response.status_code} - {response.text}")
        return False
    
    result = response.json()
    job_id = result["job_id"]
    print(f"✅ Analysis started. Job ID: {job_id}")
    
    # Poll for results
    print("⏳ Waiting for analysis to complete...")
    max_attempts = 60  # Increased for larger repositories
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(3)
        try:
            status_response = requests.get(f"{SERVICE_URL}/status/{job_id}")
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code}")
                return False
            
            status_data = status_response.json()
            print(f"  Status: {status_data['status']} (attempt {attempt + 1}/{max_attempts})")
            
            if status_data["status"] == "completed":
                print("\n🎉 Analysis completed!")
                print_results(status_data)
                return True
            elif status_data["status"] == "failed":
                print(f"❌ Analysis failed: {status_data.get('error')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Status check request failed: {e}")
        
        attempt += 1
    
    print("⏰ Timeout waiting for analysis")
    return False

def print_results(results):
    """Print analysis results in a readable format"""
    print("\n📊 Analysis Results:")
    print(f"Repository: {results['repository']}")
    print(f"Target Dependency: {results['dependency_name']}")
    
    analysis_time = results.get('analysis_time_seconds')
    if analysis_time is not None:
        print(f"Analysis Time: {analysis_time:.2f} seconds")
    else:
        print("Analysis Time: Not available")
    
    gradle_files = results.get('gradle_files_found', [])
    print(f"Gradle Files Found: {len(gradle_files)}")
    
    if gradle_files:
        print("\nGradle Files:")
        for file in gradle_files[:5]:  # Show first 5
            print(f"  📁 {file}")
        if len(gradle_files) > 5:
            print(f"  ... and {len(gradle_files) - 5} more files")
    
    matches = results.get('matches', [])
    print(f"\nDependency Matches: {len(matches)}")
    
    if matches:
        print("\nMatches Found:")
        for i, match in enumerate(matches[:3], 1):  # Show first 3
            print(f"\n  Match {i}:")
            print(f"    📄 File: {match['file_path']}")
            print(f"    📦 Current Version: {match['current_version']}")
            print(f"    🔗 Dependency Path: {' -> '.join(match['dependency_path'])}")
            print(f"    📝 Context: {match['line_context'][:100]}...")
            
            if match.get('parent_dependency'):
                print(f"    👨‍👩‍👧‍👦 Parent Dependency: {match['parent_dependency']}")
                print(f"    📦 Parent Version: {match['parent_version']}")
        
        if len(matches) > 3:
            print(f"\n  ... and {len(matches) - 3} more matches")
    else:
        print("  No matches found for the target dependency")
        if not gradle_files:
            print("  💡 No Gradle files found in repository - this might not be a Gradle project")

def main():
    """Run comprehensive tests"""
    print("🧪 Comprehensive Dependency Analysis Service Tests")
    print("=" * 60)
    
    # Test health check
    if not test_health_check():
        print("❌ Health check failed. Make sure service is running.")
        return

    test_cases = [
        {
            "repo": "prasadrg98/sample",
            "dependency": "apacheHTTPClientVersion", 
            "description": "Testing with sample repository (no Gradle files expected)"
        }
        # Add more test cases here when we find good Gradle repositories
        # {
        #     "repo": "gradle/gradle",
        #     "dependency": "junit",
        #     "description": "Testing with Gradle project itself"
        # }
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        if run_analysis_test(test_case["repo"], test_case["dependency"], test_case["description"]):
            passed += 1
            print("\n✅ Test passed!")
        else:
            failed += 1
            print("\n❌ Test failed!")
        
        print("\n" + "-" * 50)
    
    print("\n📈 Test Summary:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)