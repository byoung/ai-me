"""
Agent configuration and MCP server setup.
Handles agent-specific configuration like MCP servers and prompts.
"""
import json
import traceback
from typing import List, Dict, Any, Optional, ClassVar

from pydantic import BaseModel, Field, computed_field, ConfigDict, SecretStr
from agents import Agent, Tool, function_tool, Runner
from agents.result import RunResult
from agents.run import RunConfig
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
    
    # Static prompt sections - these don't need instance data
    MEMORY_AGENT_PROMPT: ClassVar[str] = """
🚨 MEMORY MANAGEMENT - THIS SECTION MUST BE FOLLOWED EXACTLY 🚨

YOU MUST use the read_graph tool at the START of EVERY user interaction.
The read_graph tool is DIFFERENT from all other tools - it takes NO input parameters.

CRITICAL SYNTAX FOR read_graph:
- read_graph is called with ZERO arguments
- NO curly braces: read_graph
- NO parentheses with content: read_graph() ← This is the ONLY correct form
- NO empty object: read_graph({}) ← WRONG - will cause 400 error
- NO empty string key: read_graph({"": {}}) ← WRONG - will cause 400 error  
- NO parameters at all: read_graph ← Correct but less clear
- The correct way: read_graph() with empty parentheses but NO content inside

When calling read_graph:
✅ CORRECT: read_graph() with nothing inside the parentheses
❌ WRONG: read_graph({}), read_graph({"":""}), read_graph(params={}), read_graph(data=None)

WORKFLOW FOR EVERY MESSAGE:
1. Call read_graph() immediately - retrieve all stored information
2. Check if "user" entity exists in the returned knowledge graph
3. If the user shares new information:
   a) If "user" entity doesn't exist: create_entities(
       entities=[{"name":"user","entityType":"person",
       "observations":["..."]}])
   b) If "user" entity exists: add_observations(
       observations=[{"entityName":"user","contents":["..."]}])
4. If user asks about stored info: search read_graph results and respond

TOOLS REFERENCE:
- read_graph() ← Takes ZERO parameters, returns all stored data
- create_entities(entities=[...]) ← Takes entities array
- add_observations(observations=[...]) ← Takes observations array  
- create_relations(relations=[...]) ← Takes relations array

EXAMPLES:

User says "My favorite color is blue":
1. read_graph() ← Call with empty parentheses
2. See if "user" entity exists
3. If not: create_entities(
     entities=[{"name":"user","entityType":"person",
     "observations":["favorite color is blue"]}])
4. If yes: add_observations(
     observations=[{"entityName":"user",
     "contents":["favorite color is blue"]}])
5. Reply: "Got it, I'll remember that your favorite color is blue."

User asks "What's my favorite color":
1. read_graph() ← Call with empty parentheses FIRST
2. Find "user" entity in returned graph
3. Look for observation about color
4. Reply with the stored information

MEMORY ENTITY STRUCTURE:
- Entity name: "user" (the user you're talking to)
- Entity type: "person"
- Observations: Array of facts about them (["likes red", "from NYC", "engineer"])
"""
    
    GITHUB_RESEARCHER_PROMPT: ClassVar[str] = """
You are the GitHub Researcher, responsible for researching the Bot's professional
portfolio on GitHub.

Your responsibilities:
- Search for code, projects, and commits on GitHub
- Retrieve file contents from repositories
- Provide context about technical work and contributions

GITHUB TOOLS RESTRICTIONS - IMPORTANT:
DO NOT USE ANY GITHUB TOOL MORE THAN THREE TIMES PER REQUEST.
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
    
    KB_RESEARCHER_PROMPT: ClassVar[str] = """
KNOWLEDGE BASE RESEARCH - MANDATORY TOOL USAGE:

You MUST use get_local_info tool to answer ANY questions about my background, 
experience, skills, education, projects, or expertise.

🚨 CRITICAL RULES:
1. When user asks about your background, skills, languages, experience → ALWAYS use get_local_info
2. When you don't know something → use get_local_info before saying "I don't know"
3. When user asks personal/professional questions → ALWAYS search knowledge base first
4. Never say "I'm not familiar with that" without first trying get_local_info

MANDATORY WORKFLOW:
1. User asks question about me (background, skills, experience, projects, etc.)
2. IMMEDIATELY call: get_local_info(query="[user's question]")
3. Review ALL returned documents carefully
4. Formulate first-person response from the documents
5. Include source references (file paths or document titles)

TOOL USAGE:
- get_local_info(query="Python programming languages skills") →
  retrieves all documents about my skills
- get_local_info(query="background experience") → retrieves background info
- get_local_info(query="projects I've worked on") → retrieves project info

EXAMPLES:

User asks: "What programming languages are you skilled in?"
1. Call: get_local_info(query="programming languages skills")
2. Search returned docs for language list
3. Respond: "I'm skilled in Python, Go, TypeScript, Rust, and SQL. I specialize in..."
4. Include source like: "(from team documentation)"

User asks: "What is your background in technology?"
1. Call: get_local_info(query="background experience technology")
2. Find relevant background information
3. Respond in first-person: "I specialize in backend systems and..."
4. Cite sources

CRITICAL - DO NOT:
❌ Say "I'm not familiar" without trying get_local_info first
❌ Refuse to answer without searching the knowledge base
❌ Make up information if get_local_info returns no results

Response Format:
- ALWAYS first-person (I, my, me)
- ALWAYS include source attribution
- ALWAYS use information from get_local_info results
- Format sources like: "(from team.md)" or "(from professional documentation)"
"""
    
    @computed_field
    @property
    def mcp_github_params(self) -> MCPServerParams:
        """GitHub MCP server params with token injected from instance.
        
        Implements FR-010 (Optional Tools - GitHub).
        
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
        """Time MCP server params.
        
        Implements FR-009 (Mandatory Tools - Time).
        """
        return MCPServerParams(
            command="uvx",
            args=["mcp-server-time", "--local-timezone=Etc/UTC"],
            env=None,
            description="Time MCP Server"
        )
    
    def get_mcp_memory_params(self, session_id: str) -> MCPServerParams:
        """Memory MCP server params for knowledge graph-based session memory.
        
        Implements FR-009 (Mandatory Tools - Memory), FR-013 (Memory Tool).
        
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
    
    @property
    def agent_prompt(self) -> str:
        """Generate main agent prompt."""
        return f"""
You are acting as somebody who is personifying {self.bot_full_name}.
Your primary role is to help users by answering questions about my knowledge,
experience, and expertise in technology.

CRITICAL: You are NOT an all-knowing AI. You are personifying ME, {self.bot_full_name},
a specific person. You can ONLY answer based on MY documentation OR information about
the USER stored in memory. Do NOT use your general LLM training data to answer questions.

=== CRITICAL WORKFLOW FOR EVERY USER MESSAGE ===

1. **USER PERSONAL INFO** (they share or ask about THEIR information):
   - User says "My favorite color is..." → Use memory tools to store in knowledge graph
   - User asks "What's my favorite color?" → Use memory tools to retrieve from knowledge graph
   - Call read_graph() immediately, then create_entities/add_observations for new info

2. **GITHUB/CODE QUERIES** (they ask about repositories, code, implementations):
   - User asks "What's in repo X?" → Use GitHub search_code or get_file_contents tools
   - User asks "Show me file Y" → Use get_file_contents to fetch content
   - Use available GitHub tools to search and retrieve

3. **YOUR BACKGROUND/KNOWLEDGE** (they ask about you, {self.bot_full_name}):
   - User asks "What's your experience?" → Use get_local_info to retrieve documentation
   - User asks "Do you know Carol?" → Use get_local_info to search knowledge base
   - ALWAYS use get_local_info FIRST before saying you don't know something

=== RESPONSE GUIDELINES ===

When formulating responses:
- Always refer to yourself as {self.bot_full_name} or "I"
- When mentioning employers: "Neosofia (my current employer)" or "Medidata (a prior employer)"
- Be personable, friendly, and professional
- Format GitHub URLs as complete paths: https://github.com/owner/repo/blob/main/path/file.md
- CRITICAL: Include source citations
  - Example: "Per my resume (https://github.com/byoung/ai-me/blob/main/resume.md), I worked at..."
- Add reference links section at end if GitHub sources referenced
"""
    
    async def setup_mcp_servers(self, mcp_params_list: List[MCPServerParams]):
        """Initialize and connect all MCP servers from provided parameters.
        
        Implements FR-009 (Mandatory Tools), FR-010 (Optional Tools),
        FR-012 (Tool Error Handling).
        """
        
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
        """Create the get_local_info function tool.
        
        Implements FR-002 (Knowledge Retrieval), FR-004 (Source Attribution).
        """
        
        @function_tool
        async def get_local_info(query: str) -> str:
            """get more context based on the subject of the question.
            
            Implements FR-002 (Knowledge Retrieval), FR-004 (Source Attribution).
            
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
        """Create the main ai-me agent with organized instruction sections.
        
        Implements FR-001 (Chat Interface), FR-003 (First-Person Persona),
        FR-009 (Mandatory Tools), FR-010 (Optional Tools).
        
        The agent prompt is organized into sections providing specialized
        instructions for different capabilities:
        - Main persona and response guidelines
        - Memory management (when Memory MCP is available)
        - GitHub research (when GitHub MCP is available)
        - Knowledge base research (always available via get_local_info)
        - Time utilities (when Time MCP is available)
        
        Args:
            agent_prompt: Optional prompt override. If None, builds a
                comprehensive prompt from organized sub-prompts based on
                available tools.
            mcp_params: Optional list of MCP server parameters to initialize.
                If None or empty, no MCP servers will be initialized. To use
                memory functionality, caller must explicitly pass mcp_params
                including get_mcp_memory_params(session_id) with a unique
                session_id.
            additional_tools: Optional list of additional tools to append.
            
        Returns:
            An initialized Agent instance.
        """
        # Setup MCP servers if any params provided
        mcp_servers = await self.setup_mcp_servers(mcp_params) if mcp_params else []
        
        # Store MCP servers for cleanup
        self._mcp_servers = mcp_servers

        # Build comprehensive prompt from sections if no override provided
        if agent_prompt is None:
            # Start with main agent prompt
            prompt_sections = [self.agent_prompt]
            
            # Identify available MCP servers
            has_github = any("github-mcp-server" in str(s) for s in mcp_servers)
            has_memory = any("server-memory" in str(s) for s in mcp_servers)
            has_time = any("mcp-server-time" in str(s) for s in mcp_servers)
            
            # Add KB Researcher instructions (always available)
            prompt_sections.append("\n## Knowledge Base Research")
            prompt_sections.append(self.KB_RESEARCHER_PROMPT)
            
            # NOTE: Memory and GitHub agents are now sub-agents, not inline instructions
            # (has_memory and has_github conditions removed - see handoffs section below)
            
            # Add Time utility note if time server available
            if has_time:
                prompt_sections.append("\n## Time Information")
                prompt_sections.append(
                    "You have access to time tools for getting current "
                    "date/time information."
                )
                logger.info("✓ Time server available")
            
            prompt = "\n".join(prompt_sections)
        else:
            prompt = agent_prompt
        
        logger.debug(f"Creating ai-me agent with prompt: {prompt[:100]}...")
        
        # Build tools list - get_local_info is always the default first tool
        tools = [self.get_local_info_tool()]
        
        # Append any additional tools provided
        if additional_tools:
            tools.extend(additional_tools)

        logger.info(f"Creating ai-me agent with tools: {[tool.name for tool in tools]}")

        # Separate GitHub and memory servers for sub-agent creation
        github_mcp_servers = [s for s in mcp_servers if "github-mcp-server" in str(s)]
        memory_mcp_servers = [s for s in mcp_servers if "server-memory" in str(s)]
        time_mcp_servers = [s for s in mcp_servers if "mcp-server-time" in str(s)]
        
        # Create GitHub sub-agent if GitHub server is available
        github_agent = None
        if github_mcp_servers:
            github_agent = Agent(
                name="github-agent",
                handoff_description=(
                    "Handles GitHub research and code exploration"
                ),
                instructions=self.GITHUB_RESEARCHER_PROMPT,
                tools=[],
                mcp_servers=github_mcp_servers,
                model=self.model,
            )
            logger.info(
                f"✓ GitHub sub-agent created with "
                f"{len(github_mcp_servers)} MCP server(s)"
            )
        
        # Create Memory sub-agent if memory server is available
        memory_agent = None
        if memory_mcp_servers:
            memory_agent = Agent(
                name="memory-agent",
                handoff_description="Handles memory management and knowledge graph operations",
                instructions=self.MEMORY_AGENT_PROMPT,
                tools=[],
                mcp_servers=memory_mcp_servers,
                model=self.model,
            )
            logger.info(
                f"✓ Memory sub-agent created with "
                f"{len(memory_mcp_servers)} MCP server(s)"
            )
        
        # Create main agent with ALL MCP servers for direct execution
        # Sub-agents have specialized prompts but access same tools for reliability
        agent_kwargs = {
            "model": self.model,
            "name": "ai-me",
            "instructions": prompt,
            "tools": tools,
        }
        
        if mcp_servers:
            agent_kwargs["mcp_servers"] = mcp_servers
            logger.info(f"✓ {len(mcp_servers)} MCP servers added to main agent")
        
        # Add both sub-agents as handoffs
        handoffs = []
        if github_agent:
            handoffs.append(github_agent)
        if memory_agent:
            handoffs.append(memory_agent)
        
        if handoffs:
            agent_kwargs["handoffs"] = handoffs
                
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
        """Run the agent and post-process output to remove Unicode brackets.
        
        Implements FR-001 (Chat Interface), FR-003 (First-Person Persona),
        FR-008 (Output Normalization), FR-012 (Tool Error Handling),
        NFR-001 (Sub-5s Response), NFR-003 (Structured Logging),
        NFR-004 (Unicode Normalization).
        """
        # Log user input with session context
        session_prefix = f"[Session: {self.session_id[:8]}...] " if self.session_id else ""
        json_input = {"session_id": self.session_id, "user_input": user_input}
        logger.info(json.dumps(json_input))
        
        run_config = RunConfig(tracing_disabled=True)

        try:
            result: RunResult = await Runner.run(self._agent, 
                                                 user_input, 
                                                 run_config=run_config, 
                                                 **runner_kwargs)
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
        """Cleanup MCP servers to prevent shutdown errors.
        
        Implements FR-012 (Tool Error Handling), NFR-005 (Session Isolation).
        """
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

