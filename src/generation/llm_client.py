import os
import requests
from typing import List, Optional
from dotenv import load_dotenv

# Load env variables
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:1b")


class OllamaClient:
    """Wrapper to interact with local Ollama instance for text generation."""
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = LLM_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.generate_url = f"{self.base_url}/api/generate"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Sends a generation request to local Ollama instance."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0  # Set low temperature for deterministic RAG answers
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(self.generate_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running and accessible. "
                f"You may need to run 'ollama run {self.model}' in a separate terminal."
            )
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    def generate_rag_answer(self, query: str, context_chunks: List[str]) -> str:
        """Formats the RAG prompt with context and query, then generates an answer."""
        context_str = "\n\n".join(context_chunks)
        
        prompt = (
            f"Context:\n{context_str}\n\n"
            f"Question: {query}\n\n"
            f"Instruction: Answer the question using ONLY the facts from the context above. "
            f"If the context does not contain the answer, reply with 'I cannot find the answer in the provided documents.' "
            f"Do not make up information.\n"
            f"Answer:"
        )
        
        # Pass system_prompt=None since instructions are formatted directly in the user prompt
        return self.generate(prompt, system_prompt=None)


if __name__ == "__main__":
    # Quick self-test: will fail if Ollama is not running locally
    print(f"Connecting to Ollama at {OLLAMA_BASE_URL} using model '{LLM_MODEL}'...")
    client = OllamaClient()
    try:
        ans = client.generate("Say 'Hello World' if you can read this.", system_prompt="Be concise.")
        print(f"Ollama response: {ans}")
    except Exception as e:
        print(f"Skipping active generation test: {e}")
