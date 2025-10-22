from config import Config, setup_logger
from agent import AIMeAgent
from data import DataManager, DataManagerConfig
import gradio
from gradio import Request

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
    
    # Create a NEW AIMeAgent instance for this session with session_id for logging
    session_agent = AIMeAgent(
        bot_full_name=config.bot_full_name,
        model=config.model,
        vectorstore=vectorstore,
        github_token=config.github_token,
        session_id=session_id  # Pass session_id for logging context
    )
    
    # TBD: make this prompt more generic by removing byoung/Neosofia specific references
    # The instructions are a little too verbose because the search_code tool is a PITA...
    await session_agent.create_ai_me_agent(
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
    
    # Agent now handles all logging with session context
    final_output = await session_agents[session_id].run(user_input)

    return final_output

if __name__ == "__main__":
    # Load custom CSS and JS
    with open("src/static/style.css", "r") as f:
        custom_css = f.read()
    
    with open("src/static/scroll.js", "r") as f:
        custom_js = f.read()
    
    with gradio.Blocks(
        theme='SebastianBravo/simci_css',
        css=custom_css,
        js=f"() => {{ {custom_js} }}"
    ) as ui:
        with gradio.Column(elem_id="main-column"):
            gradio.Markdown(f"""
                            # Welcome to {config.app_name}
                            The digital version of {config.bot_full_name} AKA the digital assistant 
                            that you never knew you needed ;) Feel free to ask me anything about my 
                            experience, skills, projects, and interests.
                            """)
            
            # Hidden component to trigger session initialization on page load
            session_init = gradio.Textbox(visible=False)
            
            gradio.ChatInterface(
                chat, 
                type="messages",
                chatbot=gradio.Chatbot(
                    height="65vh",
                    show_copy_button=False,
                    render_markdown=True,
                    autoscroll=False,  # Disable autoscroll to prevent jumping to bottom
                    elem_id="main-chatbot"
                )
            )
            
            # Initialize session when page loads
            ui.load(get_session_status, inputs=[], outputs=[session_init])

    ui.launch(server_name="0.0.0.0", server_port=7860, show_api=False)
