# backend/routes/chat_routes.py - COMPLETE & TESTED
from fastapi import APIRouter, HTTPException, Header
from models import ChatRequest, ChatResponse
from services.github_service import fetch_github_repo_structure
from services.llm_service import analyze_repo_with_chat
from typing import Optional
import traceback

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_repo(
    request: ChatRequest,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token")
):
    """
    Interactive chat with repository analysis
    Supports detailed diagram generation and Q&A
    """
    try:
        print(f"\n{'='*60}")
        print(f"💬 Chat Request Received")
        print(f"📦 Repository: {request.repo_url}")
        print(f"❓ Question: {request.question[:100]}...")
        print(f"🔒 Auth: {'Yes (Token provided)' if x_github_token or request.github_token else 'No (Public only)'}")
        print(f"{'='*60}\n")
        
        # Validate inputs
        if not request.repo_url or not request.repo_url.strip():
            raise HTTPException(
                status_code=400, 
                detail="Repository URL is required. Example: https://github.com/owner/repo"
            )
        
        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400, 
                detail="Question is required"
            )
        
        # Get GitHub token (prefer header, fallback to body)
        github_token = x_github_token or request.github_token
        
        # Step 1: Fetch repository data
        try:
            print("🔍 Step 1: Fetching repository structure...")
            repo_data = fetch_github_repo_structure(
                request.repo_url,
                deep_fetch=True,
                github_token=github_token
            )
            
            files_count = repo_data.get('total_files_analyzed', 0)
            print(f"✅ Repository fetched successfully!")
            print(f"   - Files analyzed: {files_count}")
            print(f"   - Languages: {', '.join(list(repo_data.get('languages', {}).keys())[:3])}")
            print()
            
        except HTTPException as e:
            # Re-raise HTTP exceptions with clear messages
            print(f"❌ Repository fetch failed: {e.detail}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error fetching repository: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch repository: {str(e)}. Please check the URL and try again."
            )
        
        # Step 2: Analyze with AI
        try:
            print("🤖 Step 2: Analyzing with AI...")
            
            # Convert chat history to proper format
            chat_history = []
            if request.chat_history:
                for msg in request.chat_history:
                    if isinstance(msg, dict):
                        chat_history.append(msg)
                    else:
                        chat_history.append({
                            "role": msg.role,
                            "content": msg.content
                        })
            
            print(f"   - Context: {len(chat_history)} previous messages")
            print(f"   - Generating detailed response...")
            
            # Analyze repository with LLM
            result = analyze_repo_with_chat(
                repo_data,
                request.question,
                chat_history
            )
            
            print(f"✅ AI analysis complete!")
            print(f"   - Answer length: {len(result['answer'])} chars")
            print(f"   - Diagram included: {result.get('has_diagram', False)}")
            if result.get('has_diagram'):
                print(f"   - Diagram type: {result.get('diagram_type', 'unknown')}")
                print(f"   - Diagram size: {len(result.get('mermaid_code', ''))} chars")
            print()
            
            print(f"{'='*60}")
            print("✨ SUCCESS: Chat response ready!")
            print(f"{'='*60}\n")
            
            return ChatResponse(
                answer=result["answer"],
                repo_name=result["repo_name"],
                has_diagram=result["has_diagram"],
                mermaid_code=result.get("mermaid_code"),
                diagram_type=result.get("diagram_type"),
                follow_up_questions=result.get("follow_up_questions", [])
            )
            
        except Exception as e:
            print(f"❌ AI analysis error: {str(e)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"AI analysis failed: {str(e)}"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    