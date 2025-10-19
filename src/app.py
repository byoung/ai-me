from config import Config
from agent import AIMeAgent
from data import DataManager, DataManagerConfig
import gradio
from gradio import Request

config = Config()

# Initialize data manager and vectorstore
data_config = DataManagerConfig(
    github_repos=config.github_repos
)
data_manager = DataManager(config=data_config)
vectorstore = data_manager.setup_vectorstore()

# Initialize agent config with vectorstore
agent_config = AIMeAgent(
    bot_full_name=config.bot_full_name,
    model=config.model,
    vectorstore=vectorstore,
    github_token=config.github_token
)

# Per-session agent storage (keyed by Gradio session_hash)
user_agents = {}


async def initialize_session(session_id: str) -> None:
    """Initialize and warmup agent for a new session."""
    if session_id in user_agents:
        return  # Already initialized
    
    print(f"\n[Session: {session_id[:8]}...] Initializing new session...")
    
    # TBD: make this prompt more generic by removing byoung/Neosofia specific references
    # The instructions are a little too verbose because the search_code tool is a PITA...
    user_agents[session_id] = await agent_config.create_ai_me_agent(    
        agent_prompt=f"""
You are acting as somebody who is personifying {config.bot_full_name}.

GITHUB TOOLS RESTRICTIONS - IMPORTANT:
DO NOT USE ANY GITHUB TOOL MORE THAN THREE TIMES PER SESSION.
You have access to these GitHub tools ONLY:
- search_code: to look for code snippets and references supporting your answers
- get_file_contents: for getting source code (NEVER download .md markdown files)
- list_commits: for getting commit history for a specific user


CRITICAL RULES FOR search_code TOOL:
The search_code tool searches ALL of GitHub by default. You MUST add owner/repo filters to EVERY search_code query.

REQUIRED FORMAT: Always include one of these filters in the query parameter:
- user:byoung (to search byoung's repos)
- org:Neosofia (to search Neosofia's repos)  
- repo:byoung/ai-me (specific repo)
- repo:Neosofia/corporate (specific repo)

EXAMPLES OF CORRECT search_code USAGE:
- search_code(query="python user:byoung")
- search_code(query="docker org:Neosofia")
- search_code(query="ReaR repo:Neosofia/corporate")

EXAMPLES OF INCORRECT search_code USAGE (NEVER DO THIS):
- search_code(query="python")
- search_code(query="ReaR")
- search_code(query="bash script")

CRITICAL RULES FOR get_file_contents TOOL:
The get_file_contents tool accepts ONLY these parameters: owner, repo, path
DO NOT use 'ref' parameter - it will cause errors. The tool always reads from the main/default branch.

EXAMPLES OF CORRECT get_file_contents USAGE:
- get_file_contents(owner="Neosofia", repo="corporate", path="website/qms/policies.md")
- get_file_contents(owner="byoung", repo="ai-me", path="README.md")

EXAMPLES OF INCORRECT get_file_contents USAGE (NEVER DO THIS):
- get_file_contents(owner="Neosofia", repo="corporate", path="website/qms/policies.md", ref="main")
- get_file_contents(owner="byoung", repo="ai-me", path="README.md", ref="master")

OTHER RULES:
 * Use get_local_info tool ONCE to gather info from markdown documentation (this is RAG-based)
 * Answer based on the information from tool calls
 * only use ASCII chars for the final output (not tool calling)
 * Do not offer follow ups -- just answer the question
 * Format file references as complete GitHub URLs with owner, repo, path, and line numbers
   Example: https://github.com/owner/repo/blob/main/filename.md#L44-L53
   Never use shorthand like: filename.md†L44-L53
 * Add reference links in a references section at the end of the output if they match github.com
 """,
        mcp_params=[agent_config.mcp_github_params,agent_config.mcp_time_params],
    )
    
    # Warmup: establish context and preload tools
    try:
        print(f"[Session: {session_id[:8]}...] Running warmup...")
        await agent_config.run("Please introduce yourself briefly - who you are and what your main expertise is.")
        print(f"[Session: {session_id[:8]}...] Warmup complete!")
    except Exception as e:
        print(f"[Session: {session_id[:8]}...] Warmup failed: {e}")


async def get_session_status(request: Request):
    """Initialize session and return status. Called on page load."""
    session_id = request.session_hash
    if session_id not in user_agents:
        await initialize_session(session_id)
    return ""


async def chat(user_input: str, history, request: Request):
    session_id = request.session_hash
    
    # Initialize agent for this session if not already done
    if session_id not in user_agents:
        await initialize_session(session_id)
    
    ai_me = user_agents[session_id]
    
    print("USER", f"[Session: {session_id[:8]}...]", "=" * 77)
    print(user_input)

    # Use agent_config.run() which handles Unicode bracket filtering
    final_output = await agent_config.run(user_input)

    print("AGENT", "=" * 94)
    print(final_output)

    return final_output

if __name__ == "__main__":
    with gradio.Blocks(theme=gradio.themes.Ocean()) as ui:
        gradio.Markdown(f"""# Welcome to {config.app_name}
                    The digital version of {config.bot_full_name}
                    The digital assistant that you never knew you needed ;)
                    Feel free to ask me anything about my experience, skills, projects, and interests.
                    """)
        
        # Hidden component to trigger session initialization on page load
        session_init = gradio.Textbox(visible=False)
        
        gradio.ChatInterface(chat, type="messages")
        
        # Initialize session when page loads
        ui.load(get_session_status, inputs=[], outputs=[session_init])

    ui.launch(server_name="0.0.0.0", server_port=7860)
