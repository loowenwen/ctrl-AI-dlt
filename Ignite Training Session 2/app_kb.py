import streamlit as st
from strands import Agent
from strands.models import BedrockModel
from strands_tools import use_llm, memory

# Import the specialized assistants
from strands_multi_agent_example.computer_science_assistant import computer_science_assistant
from strands_multi_agent_example.english_assistant import english_assistant
from strands_multi_agent_example.language_assistant import language_assistant
from strands_multi_agent_example.math_assistant import math_assistant
from strands_multi_agent_example.no_expertise import general_assistant

# Define the teacher's assistant system prompt
TEACHER_SYSTEM_PROMPT = """
You are TeachAssist, a sophisticated educational orchestrator designed to coordinate educational support across multiple subjects. Your role is to:

1. Analyze incoming student queries and determine the most appropriate specialized agent to handle them:
   - Math Agent: For mathematical calculations, problems, and concepts
   - English Agent: For writing, grammar, literature, and composition
   - Language Agent: For translation and language-related queries
   - Computer Science Agent: For programming, algorithms, data structures, and code execution
   - General Assistant: For all other topics outside these specialized domains

2. Key Responsibilities:
   - Accurately classify student queries by subject area
   - Route requests to the appropriate specialized agent
   - Maintain context and coordinate multi-step problems
   - Ensure cohesive responses when multiple agents are needed

3. Decision Protocol:
   - If query involves calculations/numbers → Math Agent
   - If query involves writing/literature/grammar → English Agent
   - If query involves translation → Language Agent
   - If query involves programming/coding/algorithms/computer science → Computer Science Agent
   - If query is outside these specialized areas → General Assistant
   - For complex queries, coordinate multiple agents as needed

Always confirm your understanding before routing to ensure accurate assistance.
"""

# System prompt to determine action
ACTION_SYSTEM_PROMPT = """
You are an assistant that determines whether a query should be handled by:
1. A teacher agent for educational questions (math, language, English, computer science, general knowledge)
2. A knowledge base agent for personal information storage and retrieval

Reply with EXACTLY ONE WORD - either "teacher" or "knowledgebase".
DO NOT include any explanations or other text.

Examples:
- "What is the capital of France?" -> "teacher"
- "How do I solve this equation: 2x + 5 = 15?" -> "teacher"
- "Translate 'hello' to Spanish" -> "teacher"
- "Remember that my birthday is July 4" -> "knowledgebase"
- "What's my birthday?" -> "knowledgebase"
- "My favorite color is blue" -> "knowledgebase"
- "What is my favorite color?" -> "knowledgebase"

Only respond with "teacher" or "knowledgebase" - no explanation, prefix, or any other text.
"""

# System prompt for knowledge base actions
KB_ACTION_SYSTEM_PROMPT = """
You are a knowledge base assistant focusing ONLY on classifying user queries.
Your task is to determine whether a user query requires STORING information to a knowledge base
or RETRIEVING information from a knowledge base.

Reply with EXACTLY ONE WORD - either "store" or "retrieve".
DO NOT include any explanations or other text.

Examples:
- "Remember that my birthday is July 4" -> "store"
- "What's my birthday?" -> "retrieve"
- "The capital of France is Paris" -> "store"
- "What is the capital of France?" -> "retrieve"
- "My name is John" -> "store" 
- "Who am I?" -> "retrieve"
- "I live in Seattle" -> "store"
- "Where do I live?" -> "retrieve"

Only respond with "store" or "retrieve" - no explanation, prefix, or any other text.
"""

# System prompt for generating answers from retrieved information
ANSWER_SYSTEM_PROMPT = """
You are a helpful knowledge assistant that provides clear, concise answers 
based on information retrieved from a knowledge base.

The information from the knowledge base contains document IDs, titles, 
content previews and relevance scores. Focus on the actual content and 
ignore the metadata.

Your responses should:
1. Be direct and to the point
2. Not mention the source of information (like document IDs or scores)
3. Not include any metadata or technical details
4. Be conversational but brief
5. Acknowledge when information is conflicting or missing
6. Begin the response with \n

When analyzing the knowledge base results:
- Higher scores (closer to 1.0) indicate more relevant results
- Look for patterns across multiple results
- Prioritize information from results with higher scores
- Ignore any JSON formatting or technical elements in the content

Example response for conflicting information:
"Based on my records, I have both July 4 and August 8 listed as your birthday. Could you clarify which date is correct?"

Example response for clear information:
"Your birthday is on July 4."

Example response for missing information:
"I don't have any information about your birthday stored."
"""

# Set up the page
st.set_page_config(page_title="TeachAssist - Educational Assistant", layout="wide")
st.title("TeachAssist - Educational Assistant")
st.write("Ask a question in any subject area or store/retrieve personal information.")

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Initialize the teacher agent
@st.cache_resource
def get_teacher_agent():
    # Specify the Bedrock ModelID
    bedrock_model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.3,
    )
    
    # Create the teacher agent with specialized tools
    return Agent(
        model=bedrock_model,
        system_prompt=TEACHER_SYSTEM_PROMPT,
        callback_handler=None,
        tools=[math_assistant, language_assistant, english_assistant, computer_science_assistant, general_assistant],
    )

# Initialize the knowledge base agent
@st.cache_resource
def get_kb_agent():
    # Specify the Bedrock ModelID
    bedrock_model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.3,
    )
    
    # Create the knowledge base agent with memory tools
    return Agent(
        model=bedrock_model,
        tools=[memory, use_llm],
    )

def determine_action(query):
    """Determine if the query should be handled by the teacher agent or knowledge base agent."""
    agent = get_kb_agent()
    
    result = agent.tool.use_llm(
        prompt=f"Query: {query}",
        system_prompt=ACTION_SYSTEM_PROMPT
    )
    
    # Clean and extract the action
    action_text = str(result).lower().strip()
    
    # Determine which agent to use
    if "teacher" in action_text:
        return "teacher"
    else:
        return "knowledgebase"

def run_kb_agent(query):
    """Process a user query with the knowledge base agent."""
    agent = get_kb_agent()
    
    # Determine the action - store or retrieve
    result = agent.tool.use_llm(
        prompt=f"Query: {query}",
        system_prompt=KB_ACTION_SYSTEM_PROMPT
    )
    
    # Clean and extract the action
    action_text = str(result).lower().strip()
    
    # Default to retrieve if response isn't clear
    if "store" in action_text:
        # For store actions, store the full query
        agent.tool.memory(action="store", content=query)
        return "I've stored this information."
    else:
        # For retrieve actions, query the knowledge base with appropriate parameters
        result = agent.tool.memory(
            action="retrieve", 
            query=query,
            min_score=0.4,  # Set reasonable minimum score threshold
            max_results=9   # Retrieve a good number of results
        )
        # Convert the result to a string to extract just the content text
        result_str = str(result)
        
        # Generate a clear, conversational answer using the retrieved information
        answer = agent.tool.use_llm(
            prompt=f"User question: \"{query}\"\n\nInformation from knowledge base:\n{result_str}\n\nStart your answer with newline character and provide a helpful answer based on this information:",
            system_prompt=ANSWER_SYSTEM_PROMPT
        )
        
        return str(answer)

# Get user input
query = st.chat_input("Ask your question here...")

if query:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(query)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # Determine which agent should handle the query
            with st.spinner("Analyzing query..."):
                action = determine_action(query)
            
            content = ""
            if action == "teacher":
                # Get the teacher agent
                teacher_agent = get_teacher_agent()
                
                # Process the query with the teacher agent
                with st.spinner("Consulting educational specialists..."):
                    response = teacher_agent(query)
                    content = str(response)
            else:
                # Process the query with the knowledge base agent
                with st.spinner("Accessing knowledge base..."):
                    content = run_kb_agent(query)
            
            # Display the response
            message_placeholder.markdown(content)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": content})
            
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
