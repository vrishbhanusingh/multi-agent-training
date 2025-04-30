import pytest
import sys
import os
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from gemini_llm import ask_gemini
except ImportError:
    # Mock class for environments without gemini_llm
    def ask_gemini(query, *args, **kwargs):
        return "This is a mock response from Gemini"

class TestGeminiIntegration:
    
    @patch('gemini_llm.ask_gemini')
    def test_gemini_response_format(self, mock_ask_gemini):
        """Test if the response from Gemini can be correctly parsed."""
        # Mock the response in the required format
        mock_ask_gemini.return_value = """
        THINKING: This is a test message that I need to analyze. It seems to be asking about the weather.
        RESPONSE: I'd be happy to discuss the weather with you. What location are you interested in?
        """
        
        # Sample request that would be passed to Gemini
        thinking_prompt = """
        You are agent_a, an AI agent in a multi-agent system.
        You received this message from agent_b: "How's the weather today?"
        First, think about what this message means and how you should respond.
        Then, generate a short response message to send back to agent_b.
        Format your response as:
        THINKING: [your analysis of the message]
        RESPONSE: [your response message to send back]
        """
        
        # Get the mock response
        gemini_output = ask_gemini(thinking_prompt)
        
        # Parse the output
        thinking_part = ""
        response_part = ""
        
        if "THINKING:" in gemini_output and "RESPONSE:" in gemini_output:
            parts = gemini_output.split("RESPONSE:")
            thinking_part = parts[0].replace("THINKING:", "").strip()
            response_part = parts[1].strip()
        
        # Assert the parsing worked correctly
        assert "This is a test message" in thinking_part
        assert "I'd be happy to discuss" in response_part
        assert thinking_part != response_part
        
    def test_gemini_import(self):
        """Test that gemini_llm.py can be imported correctly."""
        try:
            from gemini_llm import ask_gemini
            # If environment variables are set, we could do a simple call
            if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
                with patch('gemini_llm.ask_gemini', return_value="Test response"):
                    assert ask_gemini("Test query") == "Test response"
            assert callable(ask_gemini)
        except ImportError:
            pytest.skip("gemini_llm.py not available")
        except Exception as e:
            # We just want to confirm the module exists, not that it works with live API
            assert False, f"Unexpected error importing gemini_llm: {e}"
