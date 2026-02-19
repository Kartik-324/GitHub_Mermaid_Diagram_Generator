# backend/services/llm_service.py
import os
import re
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# ✅ FIX: Token budget constants
# gpt-4o has 128k context. We reserve:
#   - ~3k  for the question + chat history
#   - ~4k  for the response (max_tokens)
#   - ~121k for our system prompt (context)
# Each char ≈ 0.25 tokens, so 121k tokens ≈ 484k chars
MAX_CONTEXT_CHARS = 480_000
# File contents are the biggest culprit - cap that section separately
MAX_FILE_CONTENTS_CHARS = 300_000
MAX_FILES_IN_PROMPT = 40

def get_llm():
    """Initialize LLM"""
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.05,
        max_tokens=4096,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

def validate_diagram_completeness(mermaid_code: str, repo_data: dict) -> tuple:
    """Validate that diagram is comprehensive enough"""
    issues = []
    
    lines = mermaid_code.split('\n')
    node_count = 0
    for line in lines:
        if '[' in line and ']' in line and not line.strip().startswith('%%'):
            node_count += 1
    
    file_count = len(repo_data.get('file_contents', {}))
    
    if file_count < 20:
        min_nodes = 15
    elif file_count < 50:
        min_nodes = 25
    else:
        min_nodes = 35
    
    if node_count < min_nodes:
        issues.append(f"Diagram too simple: only {node_count} components (need {min_nodes}+)")
    
    has_subgraphs = 'subgraph' in mermaid_code.lower()
    if not has_subgraphs and file_count > 10:
        issues.append("Missing organization: no subgraphs used")
    
    return len(issues) == 0, issues

def validate_mermaid_syntax(mermaid_code: str) -> tuple:
    """Validate Mermaid syntax and return errors if any"""
    errors = []
    lines = mermaid_code.strip().split('\n')
    
    if not lines:
        return False, ["Empty diagram code"]
    
    first_line = lines[0].strip()
    valid_types = [
        'sequenceDiagram', 'graph', 'flowchart', 'classDiagram',
        'erDiagram', 'stateDiagram', 'journey', 'gantt', 'mindmap',
        'pie', 'gitGraph'
    ]
    
    if not any(first_line.startswith(t) for t in valid_types):
        errors.append(f"Invalid diagram type: {first_line[:50]}")
        return False, errors
    
    for i, line in enumerate(lines[1:], 1):
        line = line.strip()
        if not line or line.startswith('%%'):
            continue
        if line.startswith('subgraph') or line == 'end':
            continue
        
        if line.count('[') != line.count(']'):
            errors.append(f"Line {i}: Unmatched brackets")
        if line.count('(') != line.count(')'):
            errors.append(f"Line {i}: Unmatched parentheses")
        if line.count('{') != line.count('}'):
            errors.append(f"Line {i}: Unmatched braces")
    
    return len(errors) == 0, errors

def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Auto-fix common Mermaid syntax errors"""
    code = mermaid_code.strip()
    
    if code.startswith("```mermaid"):
        code = code.replace("```mermaid", "").replace("```", "").strip()
    elif code.startswith("```"):
        code = code.replace("```", "").strip()
    
    lines = code.split('\n')
    fixed_lines = []
    
    for line in lines:
        line = line.strip()
        
        if not line or line.startswith('%%'):
            fixed_lines.append(line)
            continue
        
        if line.startswith('subgraph') or line == 'end':
            fixed_lines.append(line)
            continue
        
        line = re.sub(r'-{4,}>', '-->', line)
        line = re.sub(r'\.{4,}>', '-..->', line)
        line = line.replace('===>', '-->')
        line = line.replace('....>', '-..->')
        
        if '[' in line or '(' in line or '-->' in line or '-..->' in line:
            parts = line.split('[', 1)
            if len(parts) > 1:
                before_bracket = parts[0]
                before_bracket = re.sub(r'(\w+)\s+(\w+)(?=\s*$)', r'\1_\2', before_bracket)
                line = before_bracket + '[' + parts[1]
        
        line = re.sub(r';+', ';', line)
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def extract_detailed_repo_components(repo_data: dict) -> dict:
    """Extract and categorize components from repository"""
    components = {
        'frontend_files': [], 'backend_files': [], 'services': [],
        'routes': [], 'models': [], 'components': [], 'pages': [],
        'utils': [], 'config_files': [], 'database_files': [],
        'api_endpoints': [], 'dependencies': [], 'folders': [], 'all_files': []
    }
    
    file_structure = repo_data.get('file_structure', {})
    
    def traverse_structure(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}/{key}" if path else key
                if isinstance(value, dict):
                    components['folders'].append(current_path)
                    traverse_structure(value, current_path)
                else:
                    components['all_files'].append(current_path)
                    p = current_path.lower()
                    if 'frontend' in p or 'client' in p: components['frontend_files'].append(current_path)
                    if 'backend' in p or 'server' in p: components['backend_files'].append(current_path)
                    if 'service' in p: components['services'].append(current_path)
                    if 'route' in p or 'router' in p: components['routes'].append(current_path)
                    if 'model' in p or 'schema' in p: components['models'].append(current_path)
                    if 'component' in p: components['components'].append(current_path)
                    if 'page' in p or 'view' in p: components['pages'].append(current_path)
                    if 'util' in p or 'helper' in p: components['utils'].append(current_path)
                    if current_path.endswith(('.json', '.yaml', '.yml', '.env', '.toml', '.ini')):
                        components['config_files'].append(current_path)
                    if 'database' in p or '/db' in p or current_path.endswith('.sql'):
                        components['database_files'].append(current_path)
    
    traverse_structure(file_structure)
    
    file_contents = repo_data.get('file_contents', {})
    for filename, content in file_contents.items():
        if 'requirements.txt' in filename or 'package.json' in filename or 'pyproject.toml' in filename:
            if isinstance(content, str):
                for line in content.split('\n')[:50]:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        components['dependencies'].append(line.split('==')[0].split('>=')[0].strip())
    
    return components

def build_trimmed_file_contents(repo_data: dict, max_chars: int = MAX_FILE_CONTENTS_CHARS, max_files: int = MAX_FILES_IN_PROMPT) -> str:
    """
    ✅ FIX: Build file contents section with a hard character cap.
    Prioritizes important files (api, service, model, config) over general ones.
    """
    from .github_service import format_file_contents

    file_contents = repo_data.get('file_contents', {})
    total_files = len(file_contents)

    if total_files == 0:
        return "(no files)"

    # Priority order for which files to include
    priority_purposes = ['api', 'service', 'data_model', 'middleware', 'configuration']
    priority = {}
    others = {}

    for path, data in file_contents.items():
        purpose = data.get('purpose', '') if isinstance(data, dict) else ''
        if purpose in priority_purposes:
            priority[path] = data
        else:
            others[path] = data

    # Build the trimmed dict: priority first, then fill with others up to max_files
    trimmed = dict(list(priority.items())[:max_files])
    remaining_slots = max_files - len(trimmed)
    if remaining_slots > 0:
        trimmed.update(dict(list(others.items())[:remaining_slots]))

    if total_files > max_files:
        print(f"   ⚠️ Trimmed file contents: {total_files} → {len(trimmed)} files (token budget)")

    # Format and apply char cap
    formatted = format_file_contents(trimmed, max_files=max_files)
    if len(formatted) > max_chars:
        formatted = formatted[:max_chars] + f"\n\n... [TRUNCATED: showing {max_files}/{total_files} files to stay within token limit]"

    return formatted

def analyze_repo_with_chat(repo_data: dict, question: str, chat_history: list = None) -> dict:
    """
    Analyze repository with comprehensive diagram generation.
    ✅ FIX: Hard token budget enforced - context never exceeds ~128k tokens.
    """
    llm = get_llm()
    
    if chat_history is None:
        chat_history = []
    
    from .github_service import format_file_structure
    
    components = extract_detailed_repo_components(repo_data)
    file_count = len(components['all_files'])
    min_nodes = max(15, file_count // 2)

    # ✅ FIX: Build file contents with token cap BEFORE assembling the full context
    file_contents_section = build_trimmed_file_contents(repo_data)

    # Build the folder/component summary (this is compact, no cap needed)
    def fmt_list(items, limit=30):
        shown = items[:limit]
        s = '\n'.join('   - ' + f for f in shown)
        if len(items) > limit:
            s += f'\n   ... and {len(items) - limit} more'
        return s or '   (none)'

    context = f"""
==============================================================================
REPOSITORY ANALYSIS
==============================================================================

Repository: {repo_data.get('name', 'Unknown')}
Language: {repo_data.get('language', 'Unknown')}
Total Files: {file_count}
Stars: {repo_data.get('stars', 0)} | Forks: {repo_data.get('forks', 0)}
Description: {repo_data.get('description', 'N/A')}

==============================================================================
FILE STRUCTURE:
==============================================================================
{format_file_structure(repo_data.get('file_structure', {}))}

==============================================================================
CATEGORIZED COMPONENTS:
==============================================================================

📁 FOLDERS ({len(components['folders'])}):
{fmt_list(components['folders'])}

🎨 FRONTEND ({len(components['frontend_files'])}): {fmt_list(components['frontend_files'])}
⚙️ BACKEND ({len(components['backend_files'])}): {fmt_list(components['backend_files'])}
🔧 SERVICES ({len(components['services'])}): {fmt_list(components['services'])}
🛣️ ROUTES ({len(components['routes'])}): {fmt_list(components['routes'])}
📊 MODELS ({len(components['models'])}): {fmt_list(components['models'])}
🧩 COMPONENTS ({len(components['components'])}): {fmt_list(components['components'])}
📄 PAGES ({len(components['pages'])}): {fmt_list(components['pages'])}
🛠️ UTILS ({len(components['utils'])}): {fmt_list(components['utils'])}
💾 DATABASE ({len(components['database_files'])}): {fmt_list(components['database_files'])}

==============================================================================
FILE CONTENTS (top {MAX_FILES_IN_PROMPT} most important files):
==============================================================================
{file_contents_section}

==============================================================================
README:
==============================================================================
{repo_data.get('readme', '')[:5000]}

==============================================================================
DIAGRAM REQUIREMENTS:
==============================================================================

1. Include minimum {min_nodes} components (this repo has {file_count} files)
2. Use subgraphs for each major folder
3. Use actual filenames - NO generic names like "Service" or "Component"
4. Node IDs: ONLY letters, numbers, underscores (no spaces)
5. Arrows: ONLY --> or -.-> or ==>
6. Wrap diagram in [DIAGRAM_START] ... [DIAGRAM_END]
7. NO markdown code blocks inside the diagram tags
"""

    # Sanity check: warn if still large (shouldn't happen now)
    if len(context) > MAX_CONTEXT_CHARS:
        print(f"   ⚠️ Context still large ({len(context):,} chars) - truncating")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[CONTEXT TRUNCATED TO FIT TOKEN LIMIT]"

    messages = [SystemMessage(content=context)]
    
    for msg in chat_history[-6:]:  # ✅ reduced from -10 to save tokens
        role = msg.get('role', '')
        content = msg.get('content', '')
        if role == 'user':
            messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            # Truncate old AI messages - they can be huge
            messages.append(AIMessage(content=content[:2000]))
    
    messages.append(HumanMessage(content=question))
    
    max_retries = 3
    attempt = 0
    answer = ""
    
    while attempt < max_retries:
        try:
            print(f"\n🎨 Generating diagram (attempt {attempt + 1}/{max_retries})...")
            
            response = llm.invoke(messages)
            answer_text = response.content
            
            answer, mermaid_code, diagram_type = extract_diagram_from_response(answer_text)
            
            if mermaid_code:
                mermaid_code = fix_mermaid_syntax(mermaid_code)
                is_valid_syntax, syntax_errors = validate_mermaid_syntax(mermaid_code)
                is_complete, completeness_issues = validate_diagram_completeness(mermaid_code, repo_data)
                
                if not is_valid_syntax and attempt < max_retries - 1:
                    print(f"   ❌ Syntax errors: {syntax_errors}")
                    messages.append(AIMessage(content=answer_text[:1000]))
                    messages.append(HumanMessage(content=f"SYNTAX ERRORS: {', '.join(syntax_errors[:3])}. Fix node IDs (no spaces, use underscores) and bracket matching. Regenerate."))
                    attempt += 1
                    continue
                
                if not is_complete and attempt < max_retries - 1:
                    print(f"   ⚠️ Incompleteness: {completeness_issues}")
                    messages.append(AIMessage(content=answer_text[:1000]))
                    messages.append(HumanMessage(content=f"DIAGRAM TOO SIMPLE: {', '.join(completeness_issues)}. Include at least {min_nodes} components with subgraphs. Use real filenames. Regenerate."))
                    attempt += 1
                    continue
                
                print(f"   ✅ Diagram validated successfully!")
            
            follow_ups = generate_follow_up_questions(answer, mermaid_code is not None, diagram_type)
            
            return {
                "answer": answer,
                "mermaid_code": mermaid_code,
                "diagram_type": diagram_type,
                "has_diagram": mermaid_code is not None,
                "follow_up_questions": follow_ups,
                "repo_name": repo_data.get('name', 'Unknown')
            }
        
        except Exception as e:
            err = str(e)
            print(f"   ❌ Error: {err}")
            
            # ✅ FIX: If it's a context length error, trim harder and retry once
            if "context_length_exceeded" in err or "maximum context length" in err:
                if attempt < max_retries - 1:
                    print(f"   🔪 Context too long - aggressively trimming for retry...")
                    # Rebuild with much smaller file section
                    reduced_contents = build_trimmed_file_contents(repo_data, max_chars=80_000, max_files=15)
                    # Replace the file contents section in context
                    trimmed_context = context.split("FILE CONTENTS")[0]
                    trimmed_context += f"FILE CONTENTS (reduced due to token limit):\n==============================================================================\n{reduced_contents}"
                    messages[0] = SystemMessage(content=trimmed_context)
                    attempt += 1
                    continue
            
            if attempt < max_retries - 1:
                attempt += 1
                continue
            
            return {
                "answer": f"Error generating response: {err}",
                "mermaid_code": None,
                "diagram_type": None,
                "has_diagram": False,
                "follow_up_questions": [],
                "repo_name": repo_data.get('name', 'Unknown')
            }
    
    return {
        "answer": answer if answer else "Unable to generate response",
        "mermaid_code": None,
        "diagram_type": None,
        "has_diagram": False,
        "follow_up_questions": [],
        "repo_name": repo_data.get('name', 'Unknown')
    }

def clean_mermaid_code(mermaid_code: str) -> str:
    """Clean and validate Mermaid code"""
    cleaned = fix_mermaid_syntax(mermaid_code)
    is_valid, errors = validate_mermaid_syntax(cleaned)
    if not is_valid:
        print(f"Validation warnings: {', '.join(errors)}")
    return cleaned

def detect_diagram_type(mermaid_code: str) -> str:
    """Detect the type of Mermaid diagram"""
    code_lower = mermaid_code.lower().strip()
    if code_lower.startswith("sequencediagram"): return "sequence"
    elif code_lower.startswith(("flowchart", "graph")): return "flowchart"
    elif code_lower.startswith("classdiagram"): return "class"
    elif code_lower.startswith("erdiagram"): return "database"
    elif code_lower.startswith("statediagram"): return "state"
    else: return "custom"

def extract_diagram_from_response(response_text: str) -> tuple:
    """Extract diagram code from chat response"""
    mermaid_code = None
    diagram_type = None
    answer = response_text.strip()
    
    if "[DIAGRAM_START]" in answer and "[DIAGRAM_END]" in answer:
        try:
            start_idx = answer.index("[DIAGRAM_START]") + len("[DIAGRAM_START]")
            end_idx = answer.index("[DIAGRAM_END]")
            raw_code = answer[start_idx:end_idx].strip()
            mermaid_code = clean_mermaid_code(raw_code)
            diagram_type = detect_diagram_type(mermaid_code)
            answer = answer[:answer.index("[DIAGRAM_START]")].strip()
        except Exception as e:
            print(f"Error extracting diagram: {e}")
            mermaid_code = None
            diagram_type = None
    
    return answer, mermaid_code, diagram_type

def generate_follow_up_questions(answer: str, has_diagram: bool, diagram_type: str = None) -> list:
    """Generate contextual follow-up questions"""
    if has_diagram:
        return [
            "Add more implementation details to the diagram",
            "Show error handling and edge cases",
            "Include deployment and infrastructure"
        ]
    return [
        "Create a comprehensive architecture diagram",
        "Show complete data flow with all components",
        "Generate detailed sequence diagram"
    ]