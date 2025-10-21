"""
Agent configuration and MCP server setup.
Handles agent-specific configuration like MCP servers and prompts.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, computed_field, ConfigDict, SecretStr
from agents import Agent, Tool, function_tool, Runner
from agents.result import RunResult
from agents.mcp import MCPServerStdio
from config import setup_logger
import traceback
 
logger = setup_logger(__name__)

class MCPServerParams(BaseModel):
    """Type-safe MCP server parameters."""
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    description: Optional[str] = None  # Human-readable name for debugging


class AIMeAgent(BaseModel):
    """Agent configuration including MCP servers and prompts."""
    
    bot_full_name: str
    model: str
    vectorstore: Any = Field(default=None, exclude=True)
    github_token: Optional[SecretStr] = Field(default=None, exclude=True)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @computed_field
    @property
    def mcp_github_params(self) -> MCPServerParams:
        """GitHub MCP server params with token injected from instance.
        
        Uses the official GitHub MCP server binary maintained by GitHub.
        Package: github/github-mcp-server
        GitHub: https://github.com/github/github-mcp-server
        
        The official version supports --toolsets and --read-only flags.
        We use read-only mode with a limited toolset for safety.
        """
        import os
        
        # Use local binary for testing, production path in Docker
        binary_path = "/tmp/test-github-mcp/github-mcp-server" if os.path.exists("/tmp/test-github-mcp/github-mcp-server") else "/app/bin/github-mcp-server"
        
        return MCPServerParams(
            command=binary_path,
            args=[
                "stdio",
                "--toolsets", "repos,issues,pull_requests,users",
                "--read-only"
            ],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token.get_secret_value() if self.github_token else "",
            },
            description="GitHub MCP Server (Official Binary)"
        )
    
    @computed_field
    @property
    def mcp_time_params(self) -> MCPServerParams:
        """Time MCP server params."""
        return MCPServerParams(
            command="uvx",
            args=["mcp-server-time", "--local-timezone=Etc/UTC"],
            env=None,
            description="Time MCP Server"
        )
    
    def get_mcp_memory_params(self, session_id: str) -> MCPServerParams:
        """Memory MCP server params for knowledge graph-based session memory.
        
        Creates a session-specific temporary file for memory storage to ensure complete
        isolation between sessions. Each session gets its own memory graph that is cleaned
        up when the process exits.
        
        Args:
            session_id: Unique session identifier to create isolated memory storage
            
        Returns:
            MCPServerParams configured with session-specific memory file
        """
        import tempfile
        import os
        
        # Create session-specific memory file in temp directory
        temp_dir = tempfile.gettempdir()
        memory_file = os.path.join(temp_dir, f"mcp_memory_{session_id}.json")
        
        return MCPServerParams(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            env={"MEMORY_FILE_PATH": memory_file},
            description="Memory MCP Server"
        )
    
    @computed_field
    @property
    def agent_prompt(self) -> str:
        """Generate agent prompt template."""
        return f"""
You are acting as somebody who personifying {self.bot_full_name} and must follow these rules:
 * If the user asks a question, use the get_local_info tool to gather more info
 * Answer based on the information given to you by the tool calls
 * do not offer follow up questions, just answer the question
 * Add reference links at the end of the output if they contain https://github.com
"""
    
    async def setup_mcp_servers(self, mcp_params_list: List[MCPServerParams]):
        """Initialize and connect all MCP servers from provided parameters list."""
        
        mcp_servers_local = []
        for i, params in enumerate(mcp_params_list):
            server_name = params.description or f"Server {i+1}"
            try:
                logger.info(f"Attempting to connect to {server_name}")
                logger.debug(f"Command: {params.command}")
                logger.debug(f"Args: {params.args}")
                logger.debug(f"Env vars: {list(params.env.keys()) if params.env else 'None'}")

                server = MCPServerStdio(params.model_dump(), client_session_timeout_seconds=30)
                await server.connect()
                logger.info(f"✓ {server_name} connected successfully")
                mcp_servers_local.append(server)
                
            except Exception as e:
                logger.error(f"✗ {server_name} failed to connect")
                logger.error(f"  Error type: {type(e).__name__}")
                logger.error(f"  Error message: {e}")
                # Print full traceback for debugging
                logger.error(f"  Traceback:\n{traceback.format_exc()}")
                continue

        logger.info(f"MCP Server Summary: {len(mcp_servers_local)}/{len(mcp_params_list)} connected")
        return mcp_servers_local
    
    def get_local_info_tool(self):
        """Create the get_local_info function tool."""
        
        @function_tool
        async def get_local_info(query: str) -> str:
            """get more context based on the subject of the question.
            Our vector store will contain information about our personal and professional
            experience in all things technology."""
            logger.info(f"QUERY: {query}")
            docs_content = ""
            retrieved_docs = self.vectorstore.similarity_search_with_score(query, k=5)
            logger.info(f"Retrieved {len(retrieved_docs)} documents from vector store.")
            for doc, score in retrieved_docs:
                # Handle both GitHub and local documents
                if 'github_repo' in doc.metadata:
                    github_repo = doc.metadata['github_repo']
                    file_path = doc.metadata.get('file_path', doc.metadata.get('source', 'unknown'))
                    source_link = f"https://github.com/{github_repo}/tree/main/{file_path}\n"
                else:
                    # Local document - use source path
                    source_link = f"Source: {doc.metadata.get('source', 'local document')}\n"

                logger.info({ "filename": doc.metadata.get('source', 'unknown'), "score": score })
                logger.debug(f"{doc.page_content[:100]}")

                docs_content += f"Source: {source_link}" + doc.page_content + "\n\n"

            return docs_content
        
        return get_local_info
    
    # TBD: Make the tools and mcp_servers more extensible/configurable 
    async def create_ai_me_agent(self, agent_prompt: str = None,
        mcp_params: Optional[List[MCPServerParams]] = None,
        additional_tools: Optional[List[Tool]] = None) -> Agent:
        """Create the main ai-me agent.
        
        Args:
            agent_prompt: Optional agent prompt to override default. If None, uses self.agent_prompt.
            mcp_params: Optional list of MCP server parameters to initialize. If None, no MCP servers
                will be initialized. To use memory functionality, caller must explicitly pass
                mcp_params including get_mcp_memory_params(session_id) with a unique session_id.
            additional_tools: Optional list of additional tools to append to the default get_local_info tool.
                The get_local_info tool is always included as the first tool.
        Returns:
            An initialized Agent instance.
        """
        # Setup MCP servers if any params provided
        mcp_servers = await self.setup_mcp_servers(mcp_params) if mcp_params else None

        # Use provided prompt or fall back to default
        prompt = agent_prompt if agent_prompt is not None else self.agent_prompt
        logger.debug(f"Creating ai-me agent with prompt: {prompt}")
        
        # Build tools list - get_local_info is always the default first tool
        tools = [self.get_local_info_tool()]
        
        # Append any additional tools provided
        if additional_tools:
            tools.extend(additional_tools)

        logger.info(f"Creating ai-me agent with tools: {[tool.name for tool in tools]}")

        # Pass MCP servers directly to main agent instead of wrapping in sub-agent
        agent_kwargs = {
            "model": self.model,
            "name": "ai-me",
            "instructions": prompt,
            "tools": tools,
        }
                
        # Only add mcp_servers if we have them
        if mcp_servers:
            agent_kwargs["mcp_servers"] = mcp_servers
            
        ai_me = Agent(**agent_kwargs)

        # Print all available tools after agent initialization
        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in (ai_me.tools or [])]
        logger.info(f"Available tools (direct): {', '.join(tool_names) if tool_names else 'none'}")
        
        # MCP tools are not in ai_me.tools - they're accessible via mcp_servers
        if mcp_servers:
            logger.info(f"MCP servers connected: {len(mcp_servers)}")
            # Note: MCP server tools are dynamically available but not enumerated in .tools

        # Store agent internally for use with run() method
        self._agent = ai_me

        return ai_me

    async def run(self, user_input: str, **runner_kwargs) -> str:
        """Run the agent and post-process output to remove Unicode brackets."""
        try:
            result: RunResult = await Runner.run(self._agent, user_input, **runner_kwargs)
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate limit" in error_str or "api rate limit exceeded" in error_str:
                return "⚠️ GitHub rate limit exceeded. Try asking me again in 30 seconds"
            else:
                logger.error("Unexpected error: %s", error_str)
                return """⚠️ I encountered an unexpected error. 
                My flesh and blood counterpart has been notified. 
                You can try asking me a new question or waiting a moment.
                Apologies for the inconvenience!
                Maybe I should be called 🐛 🤖
                """


        cleaned_output = result.final_output.replace("】", " ").replace("【", " ")
        return cleaned_output

