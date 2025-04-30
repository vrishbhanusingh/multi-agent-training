import os
import sys
import json
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from redis_memory import MemoryClient
from redis_state import StateClient

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

# Detect authentication method
USE_VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "False").lower() == "true"
API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
AGENT_NAME = os.getenv("AGENT_NAME", "agent_a")

# Initialize memory and state clients
memory_client = MemoryClient(agent_id=AGENT_NAME)
state_client = StateClient(agent_id=AGENT_NAME)

if USE_VERTEX:
    if not PROJECT:
        raise EnvironmentError("GOOGLE_CLOUD_PROJECT must be set for Vertex AI usage.")
    # Vertex AI initialization (assuming it's correct or handled separately)
    # For now, focusing on the non-Vertex path causing the error
    # client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION) # Keep Vertex logic if needed, but comment out if unused
    pass # Placeholder if Vertex AI part needs review later
else:
    if not API_KEY:
        raise EnvironmentError("GEMINI_API_KEY must be set for API key usage.")
    # Configure API key directly using google.generativeai
    genai.configure(api_key=API_KEY)
    # Removed: client = genai.Client(api_key=API_KEY)

def ask_gemini(query: str, model_name: str = MODEL, use_memory: bool = False) -> str: # Renamed model parameter to avoid conflict
    """
    Send a query to Gemini LLM and return the response text.
    
    Args:
        query: The prompt to send to Gemini
        model_name: The Gemini model name to use (e.g., 'gemini-1.5-flash')
        use_memory: Whether to include memory context from Redis
        
    Returns:
        str: Gemini's response text
    """
    # Include memory context if requested
    if use_memory:
        query = enrich_query_with_memory(query)
        
    # Store the thinking process in memory
    memory_client.store_thinking({
        "prompt": query,
        "timestamp": os.environ.get("TIMESTAMP", "unknown")
    })
    
    # Instantiate the model
    model_instance = genai.GenerativeModel(model_name) # Use the provided model name

    # Generate response using the model instance
    response = model_instance.generate_content(contents=query) # Use model_instance instead of client.models
    
    # Store the response in memory if it's significant
    if len(response.text) > 10: # Only store non-trivial responses
        memory_client.store_observation({
            "response": response.text,
            "model": model_name, # Use model_name
            "timestamp": os.environ.get("TIMESTAMP", "unknown")
        })
    
    return response.text

def enrich_query_with_memory(query: str) -> str:
    """
    Enhance a query with relevant memory context from Redis
    
    Args:
        query: The original query
        
    Returns:
        str: The enhanced query with memory context
    """
    # Get conversation history
    conversation_context = memory_client.get_conversation_context(max_messages=5)
    
    # Get agent state
    agent_state = state_client.get_state()
    state_context = ""
    if agent_state:
        state_context = "Your current state:\n" + json.dumps(agent_state, indent=2) + "\n\n"
    
    # Get recent thinking
    thinking_entries = memory_client.get_thinking(limit=3)
    thinking_context = ""
    if thinking_entries:
        thinking_context = "Your recent thoughts:\n"
        for entry in thinking_entries:
            if "data" in entry and "prompt" in entry["data"]:
                thinking_context += f"- {entry['data']['prompt'][:100]}...\n"
    
    # Combine all context
    memory_context = f"""
    {conversation_context}
    
    {state_context}
    
    {thinking_context}
    """
    
    # Add memory context to the query
    enhanced_query = f"""
    Memory Context:
    {memory_context}
    
    Current Query:
    {query}
    """
    
    return enhanced_query

def process_message(sender: str, content: str) -> Dict[str, str]:
    """
    Process a message from another agent with memory integration
    
    Args:
        sender: The agent that sent the message
        content: The message content
        
    Returns:
        Dict[str, str]: Dictionary with thinking and response parts
    """
    # Store the received message in memory
    memory_client.store_message({
        "sender": sender,
        "content": content,
        "received_at": os.environ.get("TIMESTAMP", "unknown")
    })
    
    # Create prompt with memory context
    thinking_prompt = f"""
    You are {AGENT_NAME}, an AI agent in a multi-agent system.
    
    You received this message from {sender}: "{content}"
    
    First, think about what this message means and how you should respond.
    Then, generate a short response message to send back to {sender}.
    
    Format your response as:
    THINKING: [your analysis of the message]
    RESPONSE: [your response message to send back]
    """
    
    # Get response with memory context
    gemini_output = ask_gemini(thinking_prompt, use_memory=True)
    
    # Parse the output
    thinking_part = ""
    response_part = ""
    
    if "THINKING:" in gemini_output and "RESPONSE:" in gemini_output:
        parts = gemini_output.split("RESPONSE:")
        thinking_part = parts[0].replace("THINKING:", "").strip()
        response_part = parts[1].strip()
    else:
        # Fallback if output format is different
        thinking_part = "Analyzing the message..."
        response_part = gemini_output
    
    # Update agent state with conversation status
    state_client.update_or_create({
        "last_interaction": {
            "with": sender,
            "content": content,
            "timestamp": os.environ.get("TIMESTAMP", "unknown")
        }
    })
    
    # Store the response in memory
    memory_client.store_message({
        "sender": AGENT_NAME,
        "recipient": sender,
        "content": response_part,
        "sent_at": os.environ.get("TIMESTAMP", "unknown")
    })
    
    return {
        "thinking": thinking_part,
        "response": response_part
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gemini_llm.py 'your question here'")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    print(ask_gemini(query))