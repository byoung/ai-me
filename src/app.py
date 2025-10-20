from config import Config, setup_logger
from agent import AIMeAgent
from data import DataManager, DataManagerConfig
import gradio
from gradio import Request
import json

logger = setup_logger(__name__)

config = Config()

# Initialize data manager and vectorstore
data_config = DataManagerConfig(
    github_repos=config.github_repos
)
data_manager = DataManager(config=data_config)
vectorstore = data_manager.setup_vectorstore()

# Per-session agent storage (keyed by Gradio session_hash)
# Each session gets its own AIMeAgent instance with session-specific MCP servers
session_agents = {}


async def initialize_session(session_id: str) -> None:
    """Initialize and warmup agent for a new session."""
    if session_id in session_agents:
        return  # Already initialized
    
    logger.info(f"[Session: {session_id[:8]}...] Initializing new session...")
    
    # Create a NEW AIMeAgent instance for this session
    session_agent = AIMeAgent(
        bot_full_name=config.bot_full_name,
        model=config.model,
        vectorstore=vectorstore,
        github_token=config.github_token
    )
    
    # TBD: make this prompt more generic by removing byoung/Neosofia specific references
    # The instructions are a little too verbose because the search_code tool is a PITA...
    await session_agent.create_ai_me_agent(
        agent_prompt=f"""
You are acting as somebody who is personifying {config.bot_full_name}.

MEMORY USAGE - MANDATORY WORKFLOW FOR EVERY USER MESSAGE:

1. FIRST ACTION - Read Current Memory:
   - Call read_graph() to see ALL existing entities and their observations
   - This prevents errors when adding observations to entities

2. User Identification:
   - Assume you are interacting with a user entity (e.g., "user_john" if they say "I'm John")
   - If the user entity doesn't exist in the graph yet, you MUST create it first

3. Gather New Information:
   - Pay attention to new information about the user:
     a) Basic Identity (name, age, gender, location, job title, education, etc.)
     b) Behaviors (interests, habits, activities, etc.)
     c) Preferences (communication style, preferred language, topics of interest, etc.)
     d) Goals (aspirations, targets, objectives, etc.)
     e) Relationships (personal and professional connections)

4. Update Memory - CRITICAL ORDER:
   - STEP 1: Create missing entities using create_entities() for any new people, organizations, or events
   - STEP 2: ONLY AFTER entities exist, add facts using add_observations() to existing entities
   - STEP 3: Connect related entities using create_relations()
   
EXAMPLE - User says "Hi, I'm Alice":
✓ Correct order:
  1. read_graph() - check if user_alice exists
  2. create_entities(entities=[{{"name": "user_alice", "entityType": "person", "observations": ["Name is Alice"]}}])
  3. respond to user

✗ WRONG - will cause errors:
  1. add_observations(entityName="user_alice", observations=["Name is Alice"]) - ERROR: entity not found!

ALWAYS create entities BEFORE adding observations to them.

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
        mcp_params=[
            session_agent.mcp_github_params,
            session_agent.mcp_time_params,
            session_agent.get_mcp_memory_params(session_id)  # Session-specific memory
        ],
    )
    
    # Store the session-specific agent
    session_agents[session_id] = session_agent
    
    # Warmup: establish context and preload tools
    try:
        logger.info(f"[Session: {session_id[:8]}...] Running warmup...")
        await session_agent.run("Please introduce yourself briefly - who you are and what your main expertise is.")
        logger.info(f"[Session: {session_id[:8]}...] Warmup complete!")
    except Exception as e:
        logger.info(f"[Session: {session_id[:8]}...] Warmup failed: {e}")


async def get_session_status(request: Request):
    """Initialize session and return status. Called on page load."""
    session_id = request.session_hash
    if session_id not in session_agents:
        await initialize_session(session_id)
    return ""


async def chat(user_input: str, history, request: Request):
    session_id = request.session_hash
    
    # Initialize agent for this session if not already done
    if session_id not in session_agents:
        await initialize_session(session_id)
    
    
    json_response = {"session_id": session_id, "user_input": user_input}
    logger.info(json_response)

    final_output = await session_agents[session_id].run(user_input)

    json_response = {"session_id": session_id, "agent_output": final_output}
    logger.info(json_response)

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
