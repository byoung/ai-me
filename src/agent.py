"""
Agent configuration and MCP server setup.
Handles agent-specific configuration like MCP servers and prompts.
"""
import json
import traceback
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, computed_field, ConfigDict, SecretStr
from agents import Agent, Tool, function_tool, Runner
from agents.result import RunResult
from agents.mcp import MCPServerStdio
from config import setup_logger
 
logger = setup_logger(__name__)

# Unicode normalization translation table - built once, reused for all responses
# Maps fancy Unicode characters to their ASCII equivalents for cleaner output
UNICODE_NORMALIZE_TABLE = str.maketrans({
    '\u202f': ' ',   # Narrow no-break space → regular space
    '\u00a0': ' ',   # Non-breaking space → regular space
    '\u2019': "'",   # Right single quotation mark → apostrophe
    '\u2018': "'",   # Left single quotation mark → apostrophe
    '\u201c': '"',   # Left double quotation mark → regular quote
    '\u201d': '"',   # Right double quotation mark → regular quote
    '\u2011': '-',   # Non-breaking hyphen → regular hyphen
    '\u2013': '-',   # En dash → regular hyphen
    '\u2014': '-',   # Em dash → regular hyphen
    '】': ' ',       # Right white corner bracket
    '【': ' ',       # Left white corner bracket
})

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
    session_id: Optional[str] = Field(default=None, exclude=True)  # For logging context
    _mcp_servers: List[Any] = []  # Store MCP servers for cleanup
    
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
        test_binary = "/tmp/test-github-mcp/github-mcp-server"
        prod_binary = "/app/bin/github-mcp-server"
        binary_path = (
            test_binary if os.path.exists(test_binary) else prod_binary
        )
        return MCPServerParams(
            command=binary_path,
            args=[
                "stdio",
                "--toolsets", "repos",
                "--read-only"
            ],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": (
                    self.github_token.get_secret_value()
                    if self.github_token else ""
                ),
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
You are acting as somebody who is personifying {self.bot_full_name}.
Your primary role is to help users by answering questions about my knowledge,
experience, and expertise in technology. When interacting with the user follow
these rules:
- always refer to yourself as {self.bot_full_name} or "I".
- When talking about a prior current or prior employer indicate the relationship
  clearly. For example: Neosofia (my current employer) or Medidata (a prior
  employer).
- You should be personable, friendly, and professional in your responses.
- You should note information about the user in your memory to improve future
  interactions.
- You should use the tools available to you to look up information as needed.
- If the user asks a question ALWAYS USE THE get_local_info tool ONCE to gather
  info from my documentation (this is RAG-based)
- Format file references as complete GitHub URLs with owner, repo, path, and
  filename
  - Example: https://github.com/owner/repo/blob/main/filename.md
  - Never use shorthand like: filename.md†L44-L53 or source†L44-L53
  - Always strip out line number references
- CRITICAL: Include source citations in your response to establish credibility
  and traceability. Format citations as:
  - For GitHub sources: "Per my [document_name]..." or "As mentioned in [document_name]..."
  - For local sources: "According to my documentation on [topic]..."
  - Include the source URL in parentheses when available
  - Example: "Per my resume (https://github.com/byoung/ai-me/blob/main/resume.md), I worked at..."
- Add reference links in a references section at the end of the output if they
  match github.com
- Below are critical instructions for using your memory and GitHub tools
  effectively.

MEMORY USAGE - MANDATORY WORKFLOW FOR EVERY USER MESSAGE:
1. FIRST ACTION - Read Current Memory:
   - Call read_graph() to see ALL existing entities and their observations
   - This prevents errors when adding observations to entities
2. User Identification:
   - Assume you are interacting with a user entity (e.g., "user_john" if they
     say "I'm John")
   - If the user entity doesn't exist in the graph yet, you MUST create it first
3. Gather New Information:
   - Pay attention to new information about the user:
     a) Basic Identity (name, age, gender, location, job title, education, etc.)
     b) Behaviors (interests, habits, activities, etc.)
     c) Preferences (communication style, preferred language, topics of
        interest, etc.)
     d) Goals (aspirations, targets, objectives, etc.)
     e) Relationships (personal and professional connections)
4. Update Memory - CRITICAL ORDER:
   - STEP 1: Create missing entities using create_entities() for any new
     people, organizations, or events
   - STEP 2: ONLY AFTER entities exist, add facts using add_observations() to
     existing entities
   - STEP 3: Connect related entities using create_relations()
EXAMPLE - User says "Hi, I'm Alice":
✓ Correct order:
  1. read_graph() - check if user_alice exists
  2. create_entities(entities=[{{"name": "user_alice", "entityType": "person",
     "observations": ["Name is Alice"]}}])
  3. respond to user
✗ WRONG - will cause errors:
  1. add_observations(entityName="user_alice",
     observations=["Name is Alice"]) - ERROR: entity not found!
ALWAYS create entities BEFORE adding observations to them.

GITHUB TOOLS RESTRICTIONS - IMPORTANT:
DO NOT USE ANY GITHUB TOOL MORE THAN THREE TIMES PER SESSION.
You have access to these GitHub tools ONLY:
- search_code: to look for code snippets and references supporting your
  answers
- get_file_contents: for getting source code (NEVER download .md markdown
  files)
- list_commits: for getting commit history for a specific user
CRITICAL RULES FOR search_code TOOL:
The search_code tool searches ALL of GitHub by default. You MUST add
owner/repo filters to EVERY search_code query.
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
DO NOT use 'ref' parameter - it will cause errors. The tool always reads from
the main/default branch.
EXAMPLES OF CORRECT get_file_contents USAGE:
- get_file_contents(owner="Neosofia", repo="corporate",
  path="website/qms/policies.md")
- get_file_contents(owner="byoung", repo="ai-me", path="README.md")
EXAMPLES OF INCORRECT get_file_contents USAGE (NEVER DO THIS):
- get_file_contents(owner="Neosofia", repo="corporate",
  path="website/qms/policies.md", ref="main")
- get_file_contents(owner="byoung", repo="ai-me", path="README.md",
  ref="master")
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

        mcp_count = len(mcp_servers_local)
        mcp_total = len(mcp_params_list)
        logger.info(f"MCP Server Summary: {mcp_count}/{mcp_total} connected")
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
                    file_path = doc.metadata.get(
                        'file_path',
                        doc.metadata.get('source', 'unknown'),
                    )
                    source_link = (
                        f"https://github.com/{github_repo}/tree/main/"
                        f"{file_path}\n"
                    )
                else:
                    # Local document - use source path
                    source = doc.metadata.get('source', 'local document')
                    source_link = f"Source: {source}\n"

                logger.info({ "filename": doc.metadata.get('source', 'unknown'), "score": score })
                logger.debug(f"{doc.page_content[:100]}")

                docs_content += f"Source: {source_link}" + doc.page_content + "\n\n"

            return docs_content
        
        return get_local_info
    
    async def create_ai_me_agent(
        self,
        agent_prompt: str = None,
        mcp_params: Optional[List[MCPServerParams]] = None,
        additional_tools: Optional[List[Tool]] = None,
    ) -> Agent:
        """Create the main ai-me agent.

        Args:
            agent_prompt: Optional prompt override. If None, uses self.agent_prompt.
            mcp_params: Optional list of MCP server parameters to initialize.
                If None, no MCP servers will be initialized. To use memory
                functionality, caller must explicitly pass mcp_params including
                get_mcp_memory_params(session_id) with a unique session_id.
            additional_tools: Optional list of additional tools to append to
                the default get_local_info tool. The get_local_info tool is
                always included as the first tool.
        Returns:
            An initialized Agent instance.
        """
        # Setup MCP servers if any params provided
        mcp_servers = await self.setup_mcp_servers(mcp_params) if mcp_params else None
        
        # Store MCP servers for cleanup
        if mcp_servers:
            self._mcp_servers = mcp_servers

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
        tool_names = [
            tool.name if hasattr(tool, "name") else str(tool)
            for tool in (ai_me.tools or [])
        ]
        tools_str = ', '.join(tool_names) if tool_names else 'none'
        logger.info(f"Available tools (direct): {tools_str}")
        
        # MCP tools are not in ai_me.tools - they're accessible via mcp_servers
        if mcp_servers:
            logger.info(f"MCP servers connected: {len(mcp_servers)}")
            # Note: MCP server tools are dynamically available but not enumerated in .tools

        # Store agent internally for use with run() method
        self._agent = ai_me

        return ai_me

    async def run(self, user_input: str, **runner_kwargs) -> str:
        """Run the agent and post-process output to remove Unicode brackets."""
        # Log user input with session context
        session_prefix = f"[Session: {self.session_id[:8]}...] " if self.session_id else ""
        json_input = {"session_id": self.session_id, "user_input": user_input}
        logger.info(json.dumps(json_input))
        
        try:
            result: RunResult = await Runner.run(self._agent, user_input, **runner_kwargs)
        except Exception as e:
            error_str = str(e).lower()
            
            if "rate limit" in error_str or "api rate limit exceeded" in error_str:
                logger.warning(f"{session_prefix}GitHub rate limit exceeded")
                return "⚠️ GitHub rate limit exceeded. Try asking me again in 30 seconds"
            else:
                logger.error(f"{session_prefix}Unexpected error: %s", error_str)
                return """⚠️ I encountered an unexpected error. 
                My flesh and blood counterpart has been notified. 
                You can try asking me a new question or waiting a moment.
                Apologies for the inconvenience!
                Maybe I should be called 🐛 🤖
                """

        # Normalize Unicode characters to ASCII equivalents in a single pass
        cleaned_output = result.final_output.translate(UNICODE_NORMALIZE_TABLE)
        
        # Log agent output with session context
        json_output = {"session_id": self.session_id, "agent_output": cleaned_output}
        logger.info(json.dumps(json_output))
        
        return cleaned_output
    
    async def cleanup(self):
        """Cleanup MCP servers to prevent shutdown errors."""
        if not self._mcp_servers:
            return
        
        session_prefix = f"[Session: {self.session_id[:8]}...] " if self.session_id else ""
        logger.debug(f"{session_prefix}Cleaning up {len(self._mcp_servers)} MCP servers...")
        
        for server in self._mcp_servers:
            try:
                await server.cleanup()
            except Exception as e:
                # Log but don't fail - best effort cleanup
                logger.debug(f"{session_prefix}Error cleaning up MCP server: {e}")
        
        self._mcp_servers = []
        logger.debug(f"{session_prefix}MCP servers cleaned up")

