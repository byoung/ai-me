from config import Config
from agent import AIMeAgent
from data import DataManager, DataManagerConfig
import gradio

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

# Lazy agent initialization
ai_me = None


async def chat(user_input: str, history):
    # TBD: Consider using a mutable structure to avoid 'global' keyword 
    global ai_me
    if ai_me is None:
        # TBD: make this prompt more generic by removing byoung/Neosofia specific references
        # The instructions are a little too verbose because the search_code tool is a PITA...
        ai_me = await agent_config.create_ai_me_agent(    
            agent_prompt=f"""
You are acting as somebody who is personifying {config.bot_full_name}.

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
 * Do not offer follow ups -- just answer the question
 * add links to sources if they match https://github.com at the end of the output in a references section
 """,
            mcp_params=[agent_config.mcp_github_params,agent_config.mcp_time_params],
        )
    
    print("================== USER ===================")
    print(user_input)

    # Use agent_config.run() which handles Unicode bracket filtering
    final_output = await agent_config.run(user_input)

    print("================== AGENT ==================")
    print(final_output)

    return final_output

if __name__ == "__main__":
    with gradio.Blocks(theme=gradio.themes.Ocean()) as ui:
        gradio.Markdown(f"""# Welcome to {config.app_name}
                    The digital version of {config.bot_full_name}
                    The digital assistant that you never knew you needed ;)
                    Feel free to ask me anything about my experience, skills, projects, and interests.
                    """)
        gradio.ChatInterface(chat, type="messages")

    ui.launch(server_name="0.0.0.0", server_port=7860)
