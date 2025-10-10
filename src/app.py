from config import Config
from agent import AIMeAgent
from data import DataManager, DataManagerConfig
from agents import Runner
import gradio
import asyncio

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
    vectorstore=vectorstore
)

# Lazy agent initialization
ai_me = None

async def chat(user_input: str, history):
    # TBD: Consider using a mutable structure to avoid 'global' keyword 
    global ai_me
    if ai_me is None:
        ai_me = await agent_config.create_ai_me_agent(agent_config.agent_prompt)
    
    print("================== USER ===================")
    print(user_input)

    result = await Runner.run(ai_me, user_input)

    print("================== AGENT ==================")
    print(result.final_output)

    return result.final_output

if __name__ == "__main__":
    with gradio.Blocks(theme=gradio.themes.Ocean()) as ui:
        gradio.Markdown(f"""# Welcome to {config.app_name}
                    The digital version of {config.bot_full_name}
                    The digital assistant that you never knew you needed ;)
                    Feel free to ask me anything about my experience, skills, projects, and interests.
                    """)
        gradio.ChatInterface(chat, type="messages")

    ui.launch()
