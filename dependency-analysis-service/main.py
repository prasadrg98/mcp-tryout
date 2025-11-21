#!/usr/bin/env python3
"""
Dependency Analysis Service
FastAPI service for analyzing Gradle dependencies in repositories
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
import tempfile
import subprocess
import shutil
import uuid
import asyncio
from typing import List, Dict, Optional
import logging
import re
from pathlib import Path
import requests
import zipfile
import io

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dependency Analysis Service",
    description="Analyze Gradle dependencies in GitHub repositories",
    version="1.0.0"
)

# Request/Response Models
class AnalysisRequest(BaseModel):
    repository: str  # "owner/repo" format
    dependency_name: str  # Target dependency to find
    github_token: Optional[str] = None  # Optional for private repos

class DependencyMatch(BaseModel):
    file_path: str
    current_version: str
    parent_dependency: Optional[str] = None
    parent_version: Optional[str] = None
    dependency_path: List[str]  # Chain from root to target dependency
    line_context: str

class AnalysisResult(BaseModel):
    repository: str
    dependency_name: str
    job_id: str
    status: str  # "processing", "completed", "failed"
    gradle_files_found: List[str]
    matches: List[DependencyMatch]
    error: Optional[str] = None
    analysis_time_seconds: Optional[float] = None

# In-memory job storage (use Redis for production)
jobs_storage: Dict[str, AnalysisResult] = {}

class DependencyAnalyzer:
    def __init__(self, work_dir: str = "/tmp/gradle_analysis"):
        self.work_dir = work_dir
        self.ensure_work_dir()
    
    def ensure_work_dir(self):
        """Ensure work directory exists"""
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)
    
    async def clone_repository(self, repository: str, github_token: Optional[str] = None) -> str:
        """
        Step 1: Clone repository to local directory
        Returns: Local directory path
        """
        job_id = str(uuid.uuid4())[:8]
        repo_dir = os.path.join(self.work_dir, f"repo_{repository.replace('/', '_')}_{job_id}")
        
        try:
            logger.info(f"Cloning repository {repository} to {repo_dir}")
            
            # Try downloading as ZIP first (faster than git clone)
            zip_url = f"https://api.github.com/repos/{repository}/zipball/main"
            headers = {}
            if github_token:
                headers["Authorization"] = f"token {github_token}"
            
            response = requests.get(zip_url, headers=headers, timeout=60)
            if response.status_code != 200:
                # Try master branch
                zip_url = f"https://api.github.com/repos/{repository}/zipball/master"
                response = requests.get(zip_url, headers=headers, timeout=60)
            
            if response.status_code == 200:
                # Extract ZIP
                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(repo_dir)
                
                # Find the actual extracted directory (GitHub creates nested folder)
                extracted_dirs = [d for d in os.listdir(repo_dir) 
                               if os.path.isdir(os.path.join(repo_dir, d))]
                if extracted_dirs:
                    actual_repo_dir = os.path.join(repo_dir, extracted_dirs[0])
                    # Move contents up one level
                    for item in os.listdir(actual_repo_dir):
                        shutil.move(os.path.join(actual_repo_dir, item), repo_dir)
                    os.rmdir(actual_repo_dir)
                
                logger.info(f"✅ Successfully downloaded repository to {repo_dir}")
                return repo_dir
            else:
                raise Exception(f"Failed to download repository: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Failed to clone repository {repository}: {e}")
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
            raise
    
    def identify_gradle_files(self, repo_dir: str) -> List[str]:
        """
        Step 2: Identify all Gradle files in repository
        Returns: List of gradle file paths
        """
        gradle_files = []
        
        logger.info(f"Scanning for Gradle files in {repo_dir}")
        
        # Patterns to look for
        gradle_patterns = [
            "*.gradle",
            "*.gradle.kts", 
            "gradle.properties"
        ]
        
        for root, dirs, files in os.walk(repo_dir):
            # Skip hidden directories and build output
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'build']
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_dir)
                
                # Check if file matches gradle patterns
                if (file.endswith('.gradle') or 
                    file.endswith('.gradle.kts') or 
                    file == 'gradle.properties'):
                    gradle_files.append(file_path)
                    logger.info(f"📁 Found Gradle file: {relative_path}")
        
        logger.info(f"✅ Found {len(gradle_files)} Gradle files")
        return gradle_files
    
    async def analyze_gradle_dependencies(self, repo_dir: str, gradle_files: List[str], dependency_name: str) -> List[DependencyMatch]:
        """
        Step 3: For each gradle file, run dependency tree and find matches
        Returns: List of dependency matches
        """
        matches = []
        
        logger.info(f"Analyzing dependencies for target: {dependency_name}")
        
        # Check if gradlew exists
        gradlew_path = os.path.join(repo_dir, "gradlew")
        gradle_cmd = []
        
        if os.path.exists(gradlew_path):
            # Use project gradle wrapper
            os.chmod(gradlew_path, 0o755)
            gradle_cmd = [gradlew_path]
            logger.info("Using project Gradle wrapper")
        else:
            # Use system gradle (if available)
            gradle_cmd = ["gradle"]
            logger.info("Using system Gradle")
        
        # Run dependency analysis for different configurations
        configurations = ["compileClasspath", "runtimeClasspath", "testCompileClasspath"]
        
        for config in configurations:
            try:
                logger.info(f"Running gradle dependencies for configuration: {config}")
                
                result = subprocess.run(
                    gradle_cmd + ["dependencies", "--configuration", config],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=120  # 2 minute timeout
                )
                
                if result.returncode == 0:
                    # Parse dependency tree output
                    config_matches = self.parse_dependency_tree(
                        result.stdout, 
                        dependency_name, 
                        config, 
                        repo_dir
                    )
                    matches.extend(config_matches)
                else:
                    logger.warning(f"⚠️ Gradle command failed for {config}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"❌ Timeout running gradle dependencies for {config}")
            except FileNotFoundError:
                logger.error("❌ Gradle not found. Please install Gradle or ensure gradlew is present")
            except Exception as e:
                logger.error(f"❌ Error analyzing {config}: {e}")
        
        # Also analyze gradle files directly for version declarations
        file_matches = self.analyze_gradle_files_directly(gradle_files, dependency_name, repo_dir)
        matches.extend(file_matches)
        
        # Remove duplicates and merge information
        unique_matches = self.merge_duplicate_matches(matches)
        
        logger.info(f"✅ Found {len(unique_matches)} unique dependency matches")
        return unique_matches
    
    def parse_dependency_tree(self, tree_output: str, dependency_name: str, configuration: str, repo_dir: str) -> List[DependencyMatch]:
        """Parse gradle dependency tree output for target dependency"""
        matches = []
        lines = tree_output.split('\n')
        
        current_path = []
        
        for line_num, line in enumerate(lines):
            # Skip empty lines and headers
            if not line.strip() or line.startswith('----'):
                continue
            
            # Check if line contains target dependency
            if dependency_name.lower() in line.lower():
                match = self.extract_dependency_info_from_line(
                    line, dependency_name, configuration, current_path, repo_dir
                )
                if match:
                    matches.append(match)
        
        return matches
    
    def extract_dependency_info_from_line(self, line: str, dependency_name: str, configuration: str, current_path: List[str], repo_dir: str) -> Optional[DependencyMatch]:
        """Extract dependency information from a single line of gradle output"""
        
        # Parse gradle dependency tree line format
        # Example: "+--- org.apache.httpcomponents:httpclient:4.5.13"
        # Example: "     +--- org.apache.logging.log4j:log4j-api:2.17.1"
        
        # Remove tree structure characters
        clean_line = re.sub(r'[+\-\\\|\s]+', '', line)
        
        # Match dependency format: group:artifact:version
        dep_pattern = r'([^:]+):([^:]+):([^:\s]+)'
        match = re.search(dep_pattern, clean_line)
        
        if match:
            group_id, artifact_id, version = match.groups()
            full_name = f"{group_id}:{artifact_id}"
            
            # Check if this matches our target dependency
            if dependency_name.lower() in full_name.lower() or dependency_name.lower() in artifact_id.lower():
                
                # Determine parent dependency (if any)
                parent_dependency = None
                parent_version = None
                dependency_path = [full_name]
                
                # If there's indentation, this might be a transitive dependency
                indent_level = len(line) - len(line.lstrip())
                if indent_level > 0 and current_path:
                    parent_dependency = current_path[-1] if current_path else None
                    dependency_path = current_path + [full_name]
                
                return DependencyMatch(
                    file_path=f"gradle_tree_{configuration}",
                    current_version=version,
                    parent_dependency=parent_dependency,
                    parent_version=parent_version,
                    dependency_path=dependency_path,
                    line_context=line.strip()
                )
        
        return None
    
    def analyze_gradle_files_directly(self, gradle_files: List[str], dependency_name: str, repo_dir: str) -> List[DependencyMatch]:
        """Analyze gradle files directly for version declarations"""
        matches = []
        
        for gradle_file in gradle_files:
            try:
                with open(gradle_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                relative_path = os.path.relpath(gradle_file, repo_dir)
                
                # Look for version variable declarations
                version_patterns = [
                    rf'{re.escape(dependency_name)}Version\s*=\s*[\'"]([^\'"]+)[\'"]',
                    rf'{re.escape(dependency_name)}\s*=\s*[\'"]([^\'"]+)[\'"]',
                    rf'({re.escape(dependency_name)}[^:]*):([^:]*):([^\s\'"]+)'
                ]
                
                for line_num, line in enumerate(lines, 1):
                    for pattern in version_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            if len(match.groups()) == 1:
                                # Version variable
                                version = match.group(1)
                                matches.append(DependencyMatch(
                                    file_path=relative_path,
                                    current_version=version,
                                    parent_dependency=None,
                                    parent_version=None,
                                    dependency_path=[f"{dependency_name}:{version}"],
                                    line_context=f"Line {line_num}: {line.strip()}"
                                ))
                            elif len(match.groups()) == 3:
                                # Direct dependency declaration
                                group, artifact, version = match.groups()
                                matches.append(DependencyMatch(
                                    file_path=relative_path,
                                    current_version=version,
                                    parent_dependency=None,
                                    parent_version=None,
                                    dependency_path=[f"{group}:{artifact}"],
                                    line_context=f"Line {line_num}: {line.strip()}"
                                ))
            
            except Exception as e:
                logger.warning(f"⚠️ Error reading gradle file {gradle_file}: {e}")
        
        return matches
    
    def merge_duplicate_matches(self, matches: List[DependencyMatch]) -> List[DependencyMatch]:
        """Remove duplicates and merge information from multiple sources"""
        unique_matches = {}
        
        for match in matches:
            # Create a unique key based on file path and version
            key = f"{match.file_path}_{match.current_version}"
            
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                # Merge additional information
                existing = unique_matches[key]
                if match.parent_dependency and not existing.parent_dependency:
                    existing.parent_dependency = match.parent_dependency
                if match.parent_version and not existing.parent_version:
                    existing.parent_version = match.parent_version
                if len(match.dependency_path) > len(existing.dependency_path):
                    existing.dependency_path = match.dependency_path
        
        return list(unique_matches.values())
    
    def cleanup_repository(self, repo_dir: str):
        """Clean up downloaded repository"""
        try:
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)
                logger.info(f"🧹 Cleaned up repository directory: {repo_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup {repo_dir}: {e}")

# Global analyzer instance
analyzer = DependencyAnalyzer()

@app.post("/analyze", response_model=Dict[str, str])
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Start dependency analysis for a repository
    Returns job ID for tracking progress
    """
    job_id = str(uuid.uuid4())
    
    # Create initial job entry
    result = AnalysisResult(
        repository=request.repository,
        dependency_name=request.dependency_name,
        job_id=job_id,
        status="processing",
        gradle_files_found=[],
        matches=[]
    )
    
    jobs_storage[job_id] = result
    
    # Start background analysis
    background_tasks.add_task(
        run_analysis,
        job_id,
        request.repository,
        request.dependency_name,
        request.github_token
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "check_url": f"/status/{job_id}"
    }

@app.get("/status/{job_id}", response_model=AnalysisResult)
async def get_analysis_status(job_id: str):
    """Get analysis status and results"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs_storage[job_id]

async def run_analysis(job_id: str, repository: str, dependency_name: str, github_token: Optional[str] = None):
    """Background task to run the complete analysis"""
    import time
    start_time = time.time()
    
    result = jobs_storage[job_id]
    repo_dir = None
    
    try:
        logger.info(f"🚀 Starting analysis job {job_id} for {repository}/{dependency_name}")
        
        # Step 1: Clone repository
        repo_dir = await analyzer.clone_repository(repository, github_token)
        
        # Step 2: Identify gradle files
        gradle_files = analyzer.identify_gradle_files(repo_dir)
        result.gradle_files_found = [os.path.relpath(f, repo_dir) for f in gradle_files]
        
        if not gradle_files:
            result.status = "completed"
            result.error = "No Gradle files found in repository"
            return
        
        # Step 3: Analyze dependencies
        matches = await analyzer.analyze_gradle_dependencies(repo_dir, gradle_files, dependency_name)
        result.matches = matches
        
        # Update final status
        result.status = "completed"
        result.analysis_time_seconds = time.time() - start_time
        
        logger.info(f"✅ Analysis completed for job {job_id}. Found {len(matches)} matches in {result.analysis_time_seconds:.2f}s")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed for job {job_id}: {e}")
        result.status = "failed"
        result.error = str(e)
        result.analysis_time_seconds = time.time() - start_time
    
    finally:
        # Step 4: Cleanup
        if repo_dir:
            analyzer.cleanup_repository(repo_dir)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "dependency-analysis-service",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Dependency Analysis Service",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /analyze - Start dependency analysis",
            "status": "GET /status/{job_id} - Check analysis status", 
            "health": "GET /health - Health check",
            "docs": "GET /docs - API documentation"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)