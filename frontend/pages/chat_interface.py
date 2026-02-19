# frontend/pages/chat_interface.py - VOICE REMOVED
import streamlit as st
import requests
from components.mermaid_renderer import render_mermaid
from utils.state_manager import (
    add_to_diagram_history, 
    clear_chat_history,
    add_to_query_history,
    get_query_suggestions
)

def render(api_endpoint):
    """Render chat interface tab - TEXT INPUT ONLY"""
    
    st.session_state['api_endpoint_current'] = api_endpoint
    
    # Repository input at the top
    with st.container():
        chat_repo_url = st.text_input( 
            "📁 GitHub Repository URL",
            key="chat_repo_url",
            placeholder="https://github.com/username/repository (public or private)"
        )
        
        if chat_repo_url and chat_repo_url != st.session_state.current_repo:
            st.session_state.current_repo = chat_repo_url
            st.session_state.chat_history = []
            
            if st.session_state.github_token:
                st.success(f"✅ Repository loaded: {chat_repo_url.split('/')[-1]} (Private access enabled)")
            else:
                st.success(f"✅ Repository loaded: {chat_repo_url.split('/')[-1]}")
    
    st.divider()
    
    # Chat container
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            display_welcome_message()
        else:
            display_chat_history()
    
    # Input area at bottom
    st.divider()
    
    st.markdown("### 💬 Ask a Question")
    
    # Suggestions
    st.markdown("**💡 Suggestions:**")
    if 'temp_input' not in st.session_state:
        st.session_state.temp_input = ""
    
    suggestions = get_query_suggestions(st.session_state.temp_input)
    
    if suggestions:
        cols = st.columns(min(len(suggestions), 3))
        for idx, suggestion in enumerate(suggestions[:3]):
            with cols[idx]:
                if st.button(suggestion, key=f"suggest_{idx}", use_container_width=True):
                    st.session_state.selected_suggestion = suggestion
                    st.rerun()
    
    # Check if a suggestion was clicked
    if 'selected_suggestion' in st.session_state and st.session_state.selected_suggestion:
        suggestion = st.session_state.selected_suggestion
        api_endpoint_stored = st.session_state.get('api_endpoint_current', api_endpoint)
        st.session_state['selected_suggestion'] = None
        if chat_repo_url:
            handle_chat_message(api_endpoint_stored, chat_repo_url, suggestion)
    
    # Text input box
    col1, col2 = st.columns([6, 1])
    
    with col1:
        user_question = st.text_input(
            "Message",
            key="user_input",
            placeholder="Ask about the repository or request a diagram...",
            label_visibility="collapsed",
            on_change=update_temp_input
        )
        
        if user_question:
            st.session_state.temp_input = user_question
    
    with col2:
        send = st.button("Send", use_container_width=True, type="primary")
    
    # Handle send
    if send and user_question and chat_repo_url:
        add_to_query_history(user_question)
        handle_chat_message(api_endpoint, chat_repo_url, user_question)
        st.session_state.temp_input = ""
        st.rerun()
    elif send and not chat_repo_url:
        st.error("Please enter a GitHub repository URL first.")
    
    # Clear chat button
    if st.session_state.chat_history:
        st.divider()
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            clear_chat_history()
            st.rerun()

def update_temp_input():
    """Callback to update temporary input for suggestions"""
    if 'user_input' in st.session_state:
        st.session_state.temp_input = st.session_state.user_input

def display_welcome_message():
    """Display welcome message when chat is empty"""
    st.markdown("### 👋 Welcome to RepoVision AI")
    st.markdown("*Analyze any GitHub repository with AI-powered insights and visualizations*")
    
    st.markdown("")
    st.markdown("#### 💡 Try asking:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📊 **Diagrams**\n\n• Show me a sequence diagram of the authentication flow\n• Create a component diagram of the system architecture\n• Visualize how the frontend communicates with the backend")
    
    with col2:
        st.info("📝 **Analysis**\n\n• Show the database schema and relationships\n• Explain the project structure and main components\n• Create a flowchart for the user registration process")

def display_chat_history():
    """Display chat history with enhanced download options"""
    
    for idx, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            with st.container():
                st.markdown(f"**👤 You**")
                st.markdown(f"> {msg['content']}")
                st.markdown("")
        else:
            with st.container():
                st.markdown(f"**🤖 RepoVision AI**")
                st.markdown(msg['content'])
                
                # Display diagram if present
                if "diagram" in msg and msg["diagram"]:
                    st.markdown("---")
                    st.markdown("**📊 Generated Diagram**")
                    
                    theme = st.session_state.get('theme', 'Dark')
                    mermaid_theme = 'dark' if theme == 'Dark' else 'default'
                    
                    # Render with enhanced error handling
                    render_success = render_mermaid(
                        msg['diagram'],
                        height=600,
                        unique_id=f"chat_{idx}",
                        theme=mermaid_theme
                    )
                    
                    if not render_success:
                        st.warning("⚠️ Diagram had rendering issues. Ask the AI to regenerate it!")
                    
                    # Export options
                    st.markdown("**💾 Export Options:**")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        with st.expander("📝 View Code"):
                            st.code(msg['diagram'], language="mermaid")
                            st.caption("Test at: https://mermaid.live")
                    
                    with col2:
                        st.download_button(
                            label="📄 .mmd",
                            data=msg['diagram'],
                            file_name=f"diagram_{idx}.mmd",
                            mime="text/plain",
                            key=f"download_mmd_{idx}",
                            use_container_width=True
                        )
                    
                    with col3:
                        if st.button("🖼️ PNG", key=f"export_png_{idx}", use_container_width=True):
                            export_diagram_as_image(msg['diagram'], 'png', idx)
                    
                    with col4:
                        if st.button("🎨 SVG", key=f"export_svg_{idx}", use_container_width=True):
                            export_diagram_as_image(msg['diagram'], 'svg', idx)
                
                # Display suggested questions
                if "suggestions" in msg and msg["suggestions"]:
                    st.markdown("---")
                    st.markdown("**💡 Suggested follow-up questions:**")
                    
                    cols = st.columns(len(msg["suggestions"]))
                    for col_idx, (col, suggestion) in enumerate(zip(cols, msg["suggestions"])):
                        with col:
                            if st.button(
                                suggestion,
                                key=f"suggestion_{idx}_{col_idx}",
                                use_container_width=True
                            ):
                                st.session_state['selected_suggestion'] = suggestion
                                st.rerun()
                
                st.markdown("---")

def export_diagram_as_image(mermaid_code: str, format_type: str, idx: int):
    """Export diagram as PNG or SVG image"""
    
    api_endpoint = st.session_state.get('api_endpoint_current')
    
    with st.spinner(f"🎨 Generating {format_type.upper()} image..."):
        try:
            response = requests.post(
                f"{api_endpoint}/export-diagram",
                json={
                    "mermaid_code": mermaid_code,
                    "format": format_type
                },
                timeout=45
            )
            
            if response.status_code == 200:
                st.download_button(
                    label=f"💾 Download {format_type.upper()}",
                    data=response.content,
                    file_name=f"diagram_{idx}.{format_type}",
                    mime=f"image/{format_type}",
                    key=f"final_download_{format_type}_{idx}_{hash(mermaid_code)}"
                )
                st.success(f"✅ {format_type.upper()} ready! Click download button above.")
            else:
                st.error(f"❌ Failed to generate {format_type.upper()}: {response.text}")
                
        except requests.exceptions.Timeout:
            st.error("⏱️ Export timed out. Try again or use a simpler diagram.")
        except Exception as e:
            st.error(f"❌ Export error: {str(e)}")

def generate_suggestions(response_text, has_diagram):
    """Generate contextual follow-up questions"""
    suggestions = []
    
    if has_diagram:
        suggestions = [
            "Can you explain this diagram in more detail?",
            "Show me a different view of this architecture",
            "What are the potential improvements?"
        ]
    else:
        response_lower = response_text.lower()
        
        if "authentication" in response_lower or "auth" in response_lower:
            suggestions = [
                "Show authentication flow diagram",
                "What security measures are implemented?",
                "Explain the token management"
            ]
        elif "database" in response_lower or "data" in response_lower:
            suggestions = [
                "Show database schema diagram",
                "How is data synchronized?",
                "What's the caching strategy?"
            ]
        elif "api" in response_lower or "endpoint" in response_lower:
            suggestions = [
                "Show API architecture diagram",
                "What endpoints are available?",
                "Explain the request flow"
            ]
        else:
            suggestions = [
                "Create a system architecture diagram",
                "Show me the main components",
                "Explain the data flow"
            ]
    
    return suggestions[:3]

def handle_chat_message(api_endpoint, repo_url, question):
    """Handle sending a chat message with GitHub token support"""
    
    with st.spinner("🤔 Thinking..."):
        payload = {
            "repo_url": repo_url,
            "question": question,
            "chat_history": st.session_state.chat_history[-5:]
        }
        
        headers = {}
        if st.session_state.github_token:
            headers["X-GitHub-Token"] = st.session_state.github_token
        
        try:
            response = requests.post(
                f"{api_endpoint}/chat",
                json=payload,
                headers=headers,
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": question
                })
                
                assistant_msg = {
                    "role": "assistant",
                    "content": answer
                }
                
                has_diagram = False
                if data.get("has_diagram") and data.get("mermaid_code"):
                    assistant_msg["diagram"] = data["mermaid_code"]
                    has_diagram = True
                    
                    add_to_diagram_history(
                        diagram_type=data.get("diagram_type", "custom"),
                        code=data["mermaid_code"],
                        repo_name=data.get("repo_name", "Unknown"),
                        prompt=question
                    )
                
                suggestions = generate_suggestions(answer, has_diagram)
                assistant_msg["suggestions"] = suggestions
                
                st.session_state.chat_history.append(assistant_msg)
                st.rerun()
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                if "rate limit" in error_detail.lower():
                    st.error("⚠️ GitHub API rate limit exceeded. Please add a GitHub token in the sidebar for private repos.")
                else:
                    st.error(f"❌ Error: {error_detail}")
        
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. Please try a more specific question.")
        except requests.exceptions.ConnectionError:
            st.error(f"🔌 Cannot connect to API. Ensure FastAPI server is running on {api_endpoint}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")