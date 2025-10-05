# Configuration
from config import config

# Data Management
from data import DataManager

# Tools
from agents.mcp import MCPServerStdio

# Agents
from agents import Runner, Agent, Tool

# UI
import gradio

###################
# Download, Load, Chunk, Vectorize and Store md files in Chroma
###################

# Use consolidated data manager
data_manager = DataManager(
    doc_load_local=config.doc_load_local,
    github_repos=config.github_repos
)
vectorstore = data_manager.setup_vectorstore(
    include_local=True,
    include_github=True
)

retriever = vectorstore.as_retriever()

###############
# Setup Tools
###############

# MCP server params from config (currently disabled by default)
all_params = config.mcp_params_list

async def setup_mcp_servers():
    """Initialize and connect all MCP servers."""
    mcp_servers_local = []
    for i, params in enumerate(all_params):
        try:
            print(f"Initializing MCP server {i+1}...")
            async with MCPServerStdio(params=params, client_session_timeout_seconds=30) as server:
                tools = await server.list_tools()
                print(f"Server {i+1} initialized successfully with {len(tools)} tools")
            # Create a new instance for actual use
            mcp_servers_local.append(MCPServerStdio(params))
        except Exception as e:
            print(f"Error initializing MCP server {i+1}: {e}")
            continue

    print(f"Created {len(mcp_servers_local)} MCP servers. Starting now...")

    for i, server in enumerate(mcp_servers_local):
        try:
            await server.connect()
            print(f"Connected to MCP server {i+1}")
        except Exception as e:
            print(f"Error connecting to MCP server {i+1}: {e}")
            continue

    return mcp_servers_local

# Lazily initialize and cache MCP servers within the active event loop
mcp_servers = None

async def ensure_mcp_servers():
    global mcp_servers
    if mcp_servers is None:
        mcp_servers = await setup_mcp_servers()

from agents import FunctionTool, function_tool

@function_tool
async def get_local_info(query: str) -> str:
    """get more context based on the subject of the question.
    Our vector store will contain information about our personal and professional experience
    in all things technology."""
    print("QUERY:", query)
    retrieved_docs = vectorstore.similarity_search(query)
    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)

    return docs_content

##############
# Agent Setup
##############

async def get_researcher(mcp_servers) -> Agent:
    researcher = Agent(
        name="Source Code Researcher",
        instructions= f"""
            You're a source code researcher that uses your tools to gather information from github.
            When searching source code, filter to only commits by the given GitHub username.
            """,
        model=config.model,
        mcp_servers=mcp_servers,
    )
    return researcher


async def get_researcher_tool(mcp_servers) -> Tool:
    researcher = await get_researcher(mcp_servers)
    return researcher.as_tool(
            tool_name="SourceCodeResearcher",
            tool_description="""
                This tool is for searching through source code repositories. 
                Use this tool if you have a github username and repo to filter on"""
        )

# researcher_tool setup requires async; initialize inside an event loop if needed
# researcher_tool = asyncio.run(get_researcher_tool(mcp_servers))

print(config.agent_prompt)
ai_me = Agent(
    model=config.model,
    name="ai-me",
    instructions=config.agent_prompt,
    tools=[get_local_info]
    # Turn off our github researcher tool until we can optimize the response time
    # The researcher tool gives a much better response when used, but it's very slow (and expensive)
    #tools=[researcher_tool, get_local_info],
)

async def chat(user_input: str, history):
    # Ensure MCP servers are initialized in this loop/task context
    await ensure_mcp_servers()
    print("================== USER ===================")
    print(user_input)

    result = await Runner.run(ai_me, user_input)

    print("================== AGENT ==================")
    print(result.final_output)
    return result.final_output

if __name__ == "__main__":
    # Launch Gradio; MCP servers are initialized lazily inside chat()
    gradio.ChatInterface(chat, type="messages").launch()


