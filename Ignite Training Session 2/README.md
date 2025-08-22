# Strands Agents: A Multi-Agent Framework for Building Intelligent Applications

Strands Agents is a powerful Python framework that enables developers to build sophisticated multi-agent systems with specialized capabilities including knowledge management, calculator functions, meta-tooling, and workflow orchestration. The framework provides seamless integration with external services and robust agent communication.

The framework offers a modular architecture where specialized agents can work together to handle complex tasks. Key features include:
- Multi-agent orchestration with specialized agents for different domains (math, language, computer science, etc.)
- Dynamic tool creation and management through meta-tooling capabilities
- Knowledge base integration for persistent information storage and retrieval
- Integration with external services like weather APIs and Amazon
- Built-in calculator functionality through MCP (Modular Communication Platform)
- Streamlit-based UI components for interactive applications

## Repository Structure
```
strands_agents/
├── mcp_examples/                    # Basic MCP server/client examples
│   ├── hello_world_mcp_client.py   # Example MCP client implementation
│   └── hello_world_mcp_server.py   # Example MCP server implementation
├── strands_calculator_mcp_agent/    # Calculator agent using MCP
├── strands_knowledgebase_agent/    # Knowledge storage and retrieval agent
├── strands_memory_agent/           # Memory management agent
├── strands_meta_tooling_agent/     # Dynamic tool creation agent
├── strands_multi_agent/            # Multi-agent orchestration examples
│   ├── teachers_assistant.py       # Main orchestrator agent
│   └── specialized agents/         # Domain-specific agents (math, language, etc.)
├── strands_nova/                   # Nova integration examples
├── strands_weather_agent/          # Weather service integration
├── strands_workflow_agent/         # Workflow orchestration agent
└── streamlit_examples/             # Streamlit UI integration examples
```

## Usage Instructions
### Prerequisites
- Python 3.10+
- uv or pip package manager
- Virtual environment (recommended)

Required Python packages:
```
boto3
mcp[cli]
nova-act
opensearch-py
pandas
retrying
strands-agents 
strands-agents-tools[mem0_memory]
streamlit
tqdm
uv
```

### Installation
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Quick Start
1. Basic Agent Usage:
```python
from strands import Agent
from strands_tools import memory

# Create a simple agent
agent = Agent(tools=[memory])

# Use the agent
response = agent("Remember that my favorite color is blue")
```

2. Running the Calculator Example:
```bash
python strands_calculator_mcp_agent_example/mcp_calculator.py
```

3. Starting the Multi-Agent Teacher Assistant:
```bash
python strands_multi_agent_example/teachers_assistant.py
```

### More Detailed Examples
1. Knowledge Base Operations:
```python
from strands import Agent
from strands_tools import memory

agent = Agent(tools=[memory])

# Store information
agent.tool.memory(action="store", content="The capital of France is Paris")

# Retrieve information
result = agent.tool.memory(
    action="retrieve",
    query="What is the capital of France?",
    min_score=0.4
)
```

2. Weather Information:
```python
from strands_weather_agent_example.weather_forecaster import weather_agent

# Get weather forecast
response = weather_agent("What's the weather like in Seattle?")
```

### Troubleshooting
Common Issues:
1. MCP Connection Errors
   - Error: "Connection refused"
   - Solution: Ensure MCP server is running on the correct port
   - Debug: `netstat -an | grep 8000`

2. Memory Tool Issues
   - Error: "Knowledge base not found"
   - Solution: Set STRANDS_KNOWLEDGE_BASE_ID environment variable
   - Debug: `export STRANDS_KNOWLEDGE_BASE_ID=your_kb_id`

3. Agent Initialization Failures
   - Error: "No tools available"
   - Solution: Verify tool imports and initialization
   - Debug: Enable verbose logging with `STRANDS_DEBUG=1`

## Data Flow
The Strands Agents framework processes data through a coordinated multi-agent system with specialized components handling different aspects of the workflow.

```ascii
User Input → Orchestrator Agent → Specialized Agents → External Services
     ↑                                    ↓
     └────────────── Response ───────────┘
```

Key Component Interactions:
1. User queries are received by the orchestrator agent (e.g., TeachAssist)
2. Orchestrator analyzes the query and routes to appropriate specialized agents
3. Specialized agents process domain-specific tasks using their tools
4. External services (MCP, APIs) are accessed as needed
5. Results are aggregated and formatted by the orchestrator
6. Responses are returned to the user in a consistent format
7. Knowledge and context are maintained across interactions
