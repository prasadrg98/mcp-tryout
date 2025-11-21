"""
Test script for Dependency Analysis Service
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

def test_analysis():
    """Test dependency analysis"""
    print(f"\n🚀 Testing dependency analysis against {SERVICE_URL}...")
    
    # Start analysis
    request_data = {
        "repository": "prasadrg98/sample",
        "dependency_name": "apacheHTTPClientVersion",
        # "github_token": "optional-token-here"
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(f"{SERVICE_URL}/analyze", json=request_data, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        print("Make sure the service is running and accessible")
        return False
    
    if response.status_code != 200:
        print(f"❌ Analysis request failed: {response.status_code} - {response.text}")
        return False
    
    result = response.json()
    job_id = result["job_id"]
    print(f"✅ Analysis started. Job ID: {job_id}")
    
    # Poll for results
    print("\n⏳ Waiting for analysis to complete...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(2)
        status_response = requests.get(f"{SERVICE_URL}/status/{job_id}")
        
        if status_response.status_code != 200:
            print(f"❌ Status check failed: {status_response.status_code}")
            return False
        
        status_data = status_response.json()
        print(f"Status: {status_data['status']}")
        
        if status_data["status"] == "completed":
            print("\n🎉 Analysis completed!")
            print_results(status_data)
            return True
        elif status_data["status"] == "failed":
            print(f"❌ Analysis failed: {status_data.get('error')}")
            return False
        
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
    
    print(f"Gradle Files Found: {len(results.get('gradle_files_found', []))}")
    
    gradle_files = results.get('gradle_files_found', [])
    if gradle_files:
        print("\nGradle Files:")
        for file in gradle_files:
            print(f"  📁 {file}")
    
    matches = results.get('matches', [])
    print(f"\nDependency Matches: {len(matches)}")
    
    if matches:
        print("\nMatches Found:")
        for i, match in enumerate(matches, 1):
            print(f"\n  Match {i}:")
            print(f"    📄 File: {match['file_path']}")
            print(f"    📦 Current Version: {match['current_version']}")
            print(f"    🔗 Dependency Path: {' -> '.join(match['dependency_path'])}")
            print(f"    📝 Context: {match['line_context']}")
            
            if match.get('parent_dependency'):
                print(f"    👨‍👩‍👧‍👦 Parent Dependency: {match['parent_dependency']}")
                print(f"    📦 Parent Version: {match['parent_version']}")
    else:
        print("  No matches found for the target dependency")
        if not gradle_files:
            print("  💡 No Gradle files found in repository - this might not be a Gradle project")

def main():
    """Run all tests"""
    print("🧪 Testing Dependency Analysis Service")
    print("=" * 50)
    
    # Test health check
    if not test_health_check():
        print("❌ Health check failed. Make sure service is running.")
        return
    
    # Test analysis
    if test_analysis():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")

if __name__ == "__main__":
    main()