"""
Agent configuration and MCP server setup.
Handles agent-specific configuration like MCP servers and prompts.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, computed_field, ConfigDict, SecretStr
from agents import Agent, Tool, function_tool, Runner
from agents.result import RunResult
from agents.mcp import MCPServerStdio
import logger

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
        
        Uses npx to run the GitHub MCP server directly without Docker.
        This works in environments without Docker daemon access (like HF Spaces).
        """
        return MCPServerParams(
            env={
                "GITHUB_TOOLSETS": "repos",
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token.get_secret_value() if self.github_token else "",
            },
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            description="GitHub MCP Server"
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
                print(f"\n=== Attempting to connect to {server_name} ===")
                print(f"Command: {params.command}")
                print(f"Args: {params.args}")
                print(f"Env vars: {list(params.env.keys()) if params.env else 'None'}")
                
                server = MCPServerStdio(params.model_dump(), client_session_timeout_seconds=30)
                print(f"MCPServerStdio instance created, calling connect()...")
                await server.connect()
                print(f"✓ {server_name} connected successfully")
                mcp_servers_local.append(server)
                
            except Exception as e:
                print(f"✗ {server_name} failed to connect")
                print(f"  Error type: {type(e).__name__}")
                print(f"  Error message: {e}")
                # Print full traceback for debugging
                import traceback
                print(f"  Traceback:\n{traceback.format_exc()}")
                continue

        print(f"\n=== MCP Server Summary: {len(mcp_servers_local)}/{len(mcp_params_list)} connected ===\n")
        return mcp_servers_local
    
    def get_local_info_tool(self):
        """Create the get_local_info function tool."""
        
        @function_tool
        async def get_local_info(query: str) -> str:
            """get more context based on the subject of the question.
            Our vector store will contain information about our personal and professional
            experience in all things technology."""
            print("QUERY:", query)
            docs_content = ""
            retrieved_docs = self.vectorstore.similarity_search_with_score(query, k=5)
            print(f"Retrieved {len(retrieved_docs)} documents from vector store.")
            for doc, score in retrieved_docs:
                # Handle both GitHub and local documents
                if 'github_repo' in doc.metadata:
                    github_repo = doc.metadata['github_repo']
                    file_path = doc.metadata.get('file_path', doc.metadata.get('source', 'unknown'))
                    source_link = f"https://github.com/{github_repo}/tree/main/{file_path}\n"
                else:
                    # Local document - use source path
                    source_link = f"Source: {doc.metadata.get('source', 'local document')}\n"

                print(f" --------------- {doc.metadata.get('source', 'unknown')} ({score}) ---------------")
                print(f"{doc.page_content[:100]}")

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
            mcp_params: Optional list of MCP server parameters to initialize. If None, defaults to
                [mcp_time_params]. Pass an empty list to disable MCP servers.
            additional_tools: Optional list of additional tools to append to the default get_local_info tool.
                The get_local_info tool is always included as the first tool.
        Returns:
            An initialized Agent instance.
        """
        # Default to just time server if not specified
        if mcp_params is None:
            mcp_params = [self.mcp_time_params]
        
        # Setup MCP servers if any params provided
        mcp_servers = await self.setup_mcp_servers(mcp_params) if mcp_params else None

        # Use provided prompt or fall back to default
        prompt = agent_prompt if agent_prompt is not None else self.agent_prompt
        print(f"Creating ai-me agent with prompt: {prompt}")
        
        # Build tools list - get_local_info is always the default first tool
        tools = [self.get_local_info_tool()]
        
        # Append any additional tools provided
        if additional_tools:
            tools.extend(additional_tools)

        print(f"Creating ai-me agent with tools: {[tool.name for tool in tools]}")

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
        print(f"Available tools: {', '.join(tool_names) if tool_names else 'none'}")

        # Store agent internally for use with run() method
        self._agent = ai_me

        return ai_me

    async def run(self, user_input: str, **runner_kwargs) -> str:
        """Run the agent and post-process output to remove Unicode brackets.
        
        This is the standard way to run ai-me agents. It wraps Runner.run and ensures
        that problematic Unicode characters (like 【 and 】) are replaced with ASCII
        equivalents in the final output.
        
        Args:
            user_input: The user's input/query
            **runner_kwargs: Additional keyword arguments to pass to Runner.run
                (e.g., max_turns, session, etc.)
        
        Returns:
            The cleaned final output string with Unicode brackets replaced
        
        Raises:
            ValueError: If no agent has been created yet
        """
        try:
            result: RunResult = await Runner.run(self._agent, user_input, **runner_kwargs)
        except Exception as e:
            # Check if this is a GitHub API rate limit error
            error_str = str(e)
            if "rate limit" in error_str.lower() or "api rate limit exceeded" in error_str.lower():
                logger.error("⚠️  GITHUB API RATE LIMIT EXCEEDED: %s", error_str)
                # Return a message informing user that GitHub tools are temporarily unavailable
                # The agent should still have access to RAG (local info) tools
                result_text = (
                    "⚠️ GitHub API rate limit exceeded. I'm currently unable to access "
                    "live GitHub data, but I can still answer questions based on my "
                    "knowledge base. Please try again in a few minutes, or ask me something "
                    "about my documented experience and projects."
                )
                return result_text
            else:
                # Re-raise if it's not a rate limit error
                raise
        
        # Post-process: replace Unicode brackets with spaces (they corrupt URLs)
        cleaned_output = result.final_output.replace("】", " ").replace("【", " ")
        
        return cleaned_output

