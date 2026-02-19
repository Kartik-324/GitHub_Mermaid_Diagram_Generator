# backend/services/github_service.py - FIXED VERSION
import os
import requests
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path
from fastapi import HTTPException

def parse_github_url(repo_url: str) -> tuple:
    """
    Parse GitHub URL to extract owner and repo name.
    ✅ FIX 1: Correctly handles subdirectory URLs like:
       https://github.com/codebasics/langchain/tree/main/4_sqldb_tshirts
       → strips to: codebasics, langchain
    ✅ FIX 2: Uses startswith prefix removal (not .replace) to avoid
       accidentally removing matching strings mid-URL
    """
    repo_url = repo_url.strip()
    
    # Remove common prefixes using startswith (not .replace to avoid mid-string matches)
    for prefix in ["https://github.com/", "http://github.com/", "github.com/", "www.github.com/"]:
        if repo_url.startswith(prefix):
            repo_url = repo_url[len(prefix):]  # ✅ slice, not replace
            break
    
    # Remove trailing slash and .git
    repo_url = repo_url.rstrip("/").replace(".git", "")
    
    # Split and validate
    parts = repo_url.split("/")
    
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL format. Expected: https://github.com/owner/repo, got: {repo_url}")
    
    owner = parts[0]
    repo_name = parts[1]
    
    # ✅ FIX: Ignore everything after owner/repo (e.g. /tree/main/subfolder, /blob/main/file.py)
    # parts[2] would be 'tree' or 'blob' if a subdirectory URL was pasted - we don't need it
    
    if not owner or not repo_name:
        raise ValueError(f"Could not extract owner/repo from URL: {repo_url}")
    
    return owner, repo_name

def check_git_installed() -> bool:
    """Check if Git is installed and accessible"""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_safe_temp_dir() -> str:
    """Get a safe temporary directory that works on all platforms"""
    try:
        base_dir = os.path.join(os.getcwd(), "temp_repos")
        os.makedirs(base_dir, exist_ok=True)
        
        import time
        import random
        unique_name = f"repo_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        temp_dir = os.path.join(base_dir, unique_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        return temp_dir
    except Exception as e:
        print(f"⚠️ Using system temp directory: {e}")
        return tempfile.mkdtemp(prefix="repovision_")

def clone_and_analyze_repo(repo_url: str, github_token: str = None) -> dict:
    """
    Clone repository to temp directory, analyze it, then delete.
    ✅ FIX 3: cleanup now happens AFTER analysis is fully complete,
       preventing race condition where temp dir was deleted while
       uvicorn's StatReload was still scanning it (caused FileNotFoundError crash).
    """
    temp_dir = None
    
    if not check_git_installed():
        raise HTTPException(
            status_code=500,
            detail="⚠️ Git is not installed on this system.\n\n"
                   "Please install Git:\n"
                   "- Windows: https://git-scm.com/download/win\n"
                   "- Mac: brew install git\n"
                   "- Linux: sudo apt-get install git\n\n"
                   "After installing, restart the terminal and backend server."
        )
    
    try:
        try:
            owner, repo_name = parse_github_url(repo_url)
            print(f"📦 Target: {owner}/{repo_name}")
        except ValueError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid repository URL: {str(e)}\n\n"
                       "Expected format: https://github.com/owner/repository"
            )
        
        try:
            temp_dir = get_safe_temp_dir()
            print(f"📁 Temp directory: {temp_dir}")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create temporary directory: {str(e)}"
            )
        
        # Build clean clone URL from parsed owner/repo (NOT the raw input URL)
        # ✅ FIX: Always construct the clone URL from parsed parts so
        #    subdirectory paths (/tree/main/...) are never included in the git URL
        base_clone_url = f"https://github.com/{owner}/{repo_name}"
        
        if github_token:
            clone_url = f"https://{github_token}@github.com/{owner}/{repo_name}"
            print(f"🔒 Using authenticated access (token provided)")
        else:
            clone_url = base_clone_url
            print(f"🌐 Using public access (no token)")
        
        print(f"⏳ Cloning repository...")
        
        is_windows = sys.platform.startswith('win')
        
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        env['GIT_ASKPASS'] = 'echo'
        
        clone_cmd = [
            "git", "clone",
            "--depth", "1",
            "--single-branch",
            clone_url,
            temp_dir
        ]
        
        try:
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
                shell=is_windows
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.lower()
                
                if "repository not found" in error_msg or "not found" in error_msg:
                    raise HTTPException(
                        status_code=404,
                        detail=f"❌ Repository '{owner}/{repo_name}' not found.\n\n"
                               "Please check:\n"
                               "1. Repository URL is correct\n"
                               "2. Repository exists and hasn't been deleted\n"
                               "3. For PRIVATE repos: Add your GitHub token in the sidebar\n\n"
                               f"Tried to access: {owner}/{repo_name}"
                    )
                elif "authentication" in error_msg or "permission denied" in error_msg or "could not read" in error_msg:
                    raise HTTPException(
                        status_code=401,
                        detail=f"🔒 Authentication failed for '{owner}/{repo_name}'.\n\n"
                               "This is a PRIVATE repository. To access it:\n\n"
                               "1. Go to: https://github.com/settings/tokens\n"
                               "2. Click 'Generate new token (classic)'\n"
                               "3. Give it a name like 'RepoVision AI'\n"
                               "4. Check the 'repo' permission\n"
                               "5. Generate and copy the token\n"
                               "6. Paste it in the sidebar under 'GitHub Token'\n\n"
                               "Note: Public repositories don't need authentication."
                    )
                elif "could not resolve host" in error_msg:
                    raise HTTPException(
                        status_code=503,
                        detail="🌐 Network error: Cannot connect to GitHub.\n\n"
                               "Please check:\n"
                               "1. Your internet connection\n"
                               "2. GitHub is not blocked by firewall\n"
                               "3. Try accessing github.com in your browser"
                    )
                elif "timeout" in error_msg or "timed out" in error_msg:
                    raise HTTPException(
                        status_code=408,
                        detail=f"⏱️ Clone operation timed out.\n\n"
                               "This usually means:\n"
                               "1. Repository is very large (>500MB)\n"
                               "2. Slow internet connection\n"
                               "3. Network issues\n\n"
                               "Try a smaller repository first to test."
                    )
                else:
                    error_display = result.stderr[:500] if result.stderr else "Unknown error"
                    raise HTTPException(
                        status_code=500,
                        detail=f"❌ Git clone failed:\n\n{error_display}\n\n"
                               "If you need help, check:\n"
                               "1. Repository URL is correct\n"
                               "2. Git is properly installed\n"
                               "3. You have internet access"
                    )
            
            print(f"✅ Repository cloned successfully!")
            
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=408,
                detail=f"⏱️ Clone timeout after 3 minutes.\n\n"
                       f"Repository '{owner}/{repo_name}' is too large or connection is slow.\n\n"
                       "Suggestions:\n"
                       "1. Try a smaller repository\n"
                       "2. Check your internet speed\n"
                       "3. Repository might be >500MB"
            )
        
        # ✅ FIX 3: Analyze FIRST, then cleanup in finally block
        # Previously cleanup printed before clone finished in some cases
        print(f"🔍 Analyzing repository structure...")
        repo_data = analyze_local_repo(temp_dir, repo_url, owner, repo_name)
        
        print(f"✨ Analysis complete!")
        print(f"   - Files analyzed: {repo_data['total_files_analyzed']}")
        print(f"   - Languages found: {len(repo_data.get('languages', {}))}")
        
        return repo_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process repository: {str(e)}"
        )
    finally:
        # Cleanup always runs after repo_data is returned (or on error)
        if temp_dir and os.path.exists(temp_dir):
            try:
                if sys.platform.startswith('win'):
                    for root, dirs, files in os.walk(temp_dir):
                        for d in dirs:
                            try:
                                os.chmod(os.path.join(root, d), 0o777)
                            except:
                                pass
                        for f in files:
                            try:
                                os.chmod(os.path.join(root, f), 0o777)
                            except:
                                pass
                
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"🗑️ Cleaned up temp directory")
            except Exception as e:
                print(f"⚠️ Warning: Could not fully clean temp directory: {e}")

def analyze_local_repo(repo_path: str, repo_url: str, owner: str = None, repo_name: str = None) -> dict:
    """
    Analyze locally cloned repository.
    ✅ FIX: Accept pre-parsed owner/repo_name to avoid re-parsing
       (re-parsing was redundant and could fail on subdirectory URLs)
    """
    if not owner or not repo_name:
        owner, repo_name = parse_github_url(repo_url)
    
    # Try to get repo info from GitHub API (for metadata)
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    
    try:
        repo_response = requests.get(api_url, headers=headers, timeout=10)
        repo_info = repo_response.json() if repo_response.status_code == 200 else {}
    except Exception as e:
        print(f"⚠️ Could not fetch GitHub API metadata: {e}")
        repo_info = {}
    
    print("📂 Building file tree...")
    file_structure = build_file_tree_from_disk(repo_path)
    
    print("📄 Reading important files for detailed analysis...")
    file_contents = read_important_files(repo_path)
    
    print(f"✅ Read {len(file_contents)} files")
    
    readme_content = read_readme_from_disk(repo_path)
    languages = detect_languages(repo_path)
    dependencies = analyze_dependencies_from_disk(repo_path)
    
    return {
        "name": repo_info.get("name", repo_name),
        "description": repo_info.get("description", ""),
        "language": repo_info.get("language", detect_primary_language(languages)),
        "languages": languages,
        "file_structure": file_structure,
        "file_contents": file_contents,
        "dependencies": dependencies,
        "readme": readme_content,
        "stars": repo_info.get("stargazers_count", 0),
        "forks": repo_info.get("forks_count", 0),
        "open_issues": repo_info.get("open_issues_count", 0),
        "topics": repo_info.get("topics", []),
        "total_files_analyzed": len(file_contents)
    }

def build_file_tree_from_disk(repo_path: str, max_depth: int = 6) -> dict:
    """Build file tree from local repository"""
    
    skip_dirs = {
        '.git', 'node_modules', '__pycache__', '.next', 'dist', 'build',
        'coverage', '.venv', 'venv', 'env', '.idea', '.vscode', 'target',
        '.pytest_cache', '.mypy_cache', '__pypackages__', 'eggs', '.eggs',
        'vendor', 'bower_components', '.bundle'
    }
    
    def build_tree(path: str, depth: int = 0) -> dict:
        if depth > max_depth:
            return {}
        
        tree = {}
        try:
            items = os.listdir(path)
        except PermissionError:
            return {}
        
        for item in items:
            if item.startswith('.') and item not in ['.env', '.gitignore', '.env.example', '.github']:
                continue
            
            item_path = os.path.join(path, item)
            
            try:
                if os.path.isdir(item_path):
                    if item not in skip_dirs:
                        subtree = build_tree(item_path, depth + 1)
                        if subtree:
                            tree[item] = {
                                "type": "dir",
                                "path": os.path.relpath(item_path, repo_path).replace('\\', '/'),
                                "contents": subtree
                            }
                else:
                    size = os.path.getsize(item_path)
                    extension = item.split(".")[-1] if "." in item else "none"
                    purpose = classify_file_purpose(item, os.path.relpath(item_path, repo_path))
                    
                    tree[item] = {
                        "type": "file",
                        "path": os.path.relpath(item_path, repo_path).replace('\\', '/'),
                        "size": size,
                        "extension": extension,
                        "purpose": purpose
                    }
            except (PermissionError, OSError):
                continue
        
        return tree
    
    return build_tree(repo_path)

def classify_file_purpose(filename: str, filepath: str) -> str:
    """Classify file purpose for better diagram organization"""
    name_lower = filename.lower()
    
    if any(x in name_lower for x in ["test", "spec", ".test.", "_test", "test_"]):
        return "testing"
    if any(x in name_lower for x in ["config", "setup", ".env", "settings", "conf"]):
        return "configuration"
    if any(x in name_lower for x in ["model", "schema", "entity", "dto"]):
        return "data_model"
    if any(x in name_lower for x in ["route", "endpoint", "api", "controller", "handler"]):
        return "api"
    if any(x in name_lower for x in ["component", "view", "page", "screen", "template"]):
        return "ui"
    if any(x in name_lower for x in ["util", "helper", "tool", "common"]):
        return "utility"
    if any(x in name_lower for x in ["service", "provider", "manager", "factory"]):
        return "service"
    if any(x in name_lower for x in ["middleware", "interceptor", "filter"]):
        return "middleware"
    if any(x in name_lower for x in ["migration", "seed", "database", "db", ".sql"]):
        return "database"
    if filename in ["package.json", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"]:
        return "dependencies"
    if any(x in name_lower for x in ["readme", "doc", "docs", ".md"]):
        return "documentation"
    
    return "general"

def read_important_files(repo_path: str, max_files: int = 200) -> dict:
    """Read important files from repository"""
    important_files = {}
    
    code_extensions = {
        'py', 'js', 'jsx', 'ts', 'tsx', 'java', 'go', 'rs', 'cpp', 'c', 'h',
        'rb', 'php', 'swift', 'kt', 'kts', 'scala', 'sh', 'bash', 'yml', 'yaml', 
        'json', 'xml', 'md', 'txt', 'toml', 'ini', 'cfg', 'env', 'sql', 'graphql',
        'vue', 'svelte', 'css', 'scss', 'sass', 'html', 'htm'
    }
    
    skip_dirs = {
        '.git', 'node_modules', '__pycache__', '.next', 'dist', 'build',
        'coverage', '.venv', 'venv', 'env', '.idea', '.vscode', 'target',
        '.pytest_cache', '.mypy_cache', '__pypackages__', 'vendor'
    }
    
    file_count = 0
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        
        for file in files:
            if file_count >= max_files:
                break
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path).replace('\\', '/')
            
            extension = file.split(".")[-1] if "." in file else ""
            
            try:
                size = os.path.getsize(file_path)
            except OSError:
                continue
            
            should_read = (
                extension in code_extensions or 
                file in [
                    "package.json", "requirements.txt", "Dockerfile", "README.md",
                    "docker-compose.yml", "Makefile", ".env.example", "pyproject.toml",
                    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "tsconfig.json"
                ]
            )
            
            if should_read and size < 400000:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    purpose = classify_file_purpose(file, rel_path)
                    
                    important_files[rel_path] = {
                        "content": content[:40000],
                        "size": size,
                        "extension": extension,
                        "purpose": purpose,
                        "full_size": len(content)
                    }
                    
                    file_count += 1
                    
                except Exception:
                    continue
        
        if file_count >= max_files:
            break
    
    return important_files

def read_readme_from_disk(repo_path: str) -> str:
    """Read README file from repository"""
    readme_files = ["README.md", "README.txt", "README.rst", "README", "readme.md", "Readme.md"]
    
    for readme_name in readme_files:
        readme_path = os.path.join(repo_path, readme_name)
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception:
                continue
    
    return ""

def detect_languages(repo_path: str) -> dict:
    """Detect programming languages in repository"""
    languages = {}
    
    language_extensions = {
        'Python': ['.py', '.pyw'],
        'JavaScript': ['.js', '.jsx', '.mjs'],
        'TypeScript': ['.ts', '.tsx'],
        'Java': ['.java'],
        'Go': ['.go'],
        'Rust': ['.rs'],
        'C++': ['.cpp', '.cc', '.cxx', '.hpp'],
        'C': ['.c', '.h'],
        'Ruby': ['.rb'],
        'PHP': ['.php'],
        'Swift': ['.swift'],
        'Kotlin': ['.kt', '.kts'],
        'Scala': ['.scala'],
        'HTML': ['.html', '.htm'],
        'CSS': ['.css', '.scss', '.sass', '.less'],
        'Shell': ['.sh', '.bash'],
        'SQL': ['.sql'],
        'Vue': ['.vue'],
        'Svelte': ['.svelte']
    }
    
    skip_dirs = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'vendor'}
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            for lang, exts in language_extensions.items():
                if ext in exts:
                    languages[lang] = languages.get(lang, 0) + 1
    
    return languages

def detect_primary_language(languages: dict) -> str:
    """Detect primary language from language counts"""
    if not languages:
        return "Unknown"
    return max(languages, key=languages.get)

def analyze_dependencies_from_disk(repo_path: str) -> dict:
    """Analyze dependencies from dependency files"""
    dependencies = {}
    
    dependency_files = {
        "package.json": "npm",
        "yarn.lock": "yarn",
        "requirements.txt": "pip",
        "Pipfile": "pipenv",
        "pyproject.toml": "poetry",
        "Cargo.toml": "cargo",
        "go.mod": "go",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "build.gradle.kts": "gradle",
        "composer.json": "composer",
        "Gemfile": "bundler"
    }
    
    for dep_file, package_manager in dependency_files.items():
        file_path = os.path.join(repo_path, dep_file)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                dependencies[package_manager] = content[:10000]
            except Exception:
                continue
    
    return dependencies

def format_file_structure(structure: dict, indent: int = 0, max_items: int = 150) -> str:
    """Format file structure for display"""
    result = []
    count = 0
    
    for name, info in structure.items():
        if count >= max_items:
            result.append(f"{'  ' * indent}... ({len(structure) - count} more items)")
            break
            
        prefix = "  " * indent
        if isinstance(info, dict):
            if info.get("type") == "dir":
                result.append(f"{prefix}📁 {name}/")
                if "contents" in info and info["contents"]:
                    result.append(format_file_structure(info["contents"], indent + 1, max_items))
            else:
                purpose = info.get("purpose", "")
                size = info.get("size", 0)
                ext = info.get("extension", "")
                result.append(f"{prefix}📄 {name} [{ext}] ({purpose}, {size}B)")
        count += 1
    
    return "\n".join(result)

def format_file_contents(contents: dict, max_files: int = 60) -> str:
    """Format file contents for prompt"""
    result = []
    
    for filepath, file_data in list(contents.items())[:max_files]:
        if isinstance(file_data, dict):
            content = file_data.get("content", "")
            purpose = file_data.get("purpose", "")
            extension = file_data.get("extension", "")
            full_size = file_data.get("full_size", 0)
            
            result.append(f"\n{'='*60}")
            result.append(f"FILE: {filepath}")
            result.append(f"Type: {extension} | Purpose: {purpose} | Size: {full_size}B")
            result.append(f"{'='*60}")
            result.append(content[:6000])
            if full_size > 6000:
                result.append(f"\n... (truncated, {full_size - 6000} bytes remaining)")
        else:
            result.append(f"\n{'='*60}")
            result.append(f"FILE: {filepath}")
            result.append(f"{'='*60}")
            result.append(str(file_data)[:3000])
    
    return "\n".join(result)

# Keep old function name for backward compatibility
def fetch_github_repo_structure(repo_url: str, deep_fetch: bool = True, github_token: str = None) -> dict:
    """Main entry point - uses git clone for comprehensive analysis"""
    return clone_and_analyze_repo(repo_url, github_token)