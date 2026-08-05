import os
import re
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class LLMSynthesisService:
    """Service for LLM answer synthesis and query intent filter extraction."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        load_dotenv()
        self.explicit_provider = provider
        self.provider = provider or os.getenv("LLM_PROVIDER")
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model_name or os.getenv("LLM_MODEL")

        if not self.provider:
            self._resolve_provider()

    def _resolve_provider(self) -> None:
        if self.explicit_provider:
            return
        load_dotenv()
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if deepseek_key and deepseek_key != "your_deepseek_api_key_here":
            self.provider = "deepseek"
            self.api_key = deepseek_key
        elif openai_key and openai_key != "your_openai_api_key_here":
            self.provider = "openai"
            self.api_key = openai_key
        elif anthropic_key and anthropic_key != "your_anthropic_api_key_here":
            self.provider = "claude"
            self.api_key = anthropic_key
        elif os.getenv("OLLAMA_BASE_URL"):
            self.provider = "ollama"
        else:
            self.provider = "fallback"



    def extract_query_filters(self, query: str) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        query_lower = query.lower()

        state_patterns = {
            "Virginia": r"\b(virginia|va)\b",
            "California": r"\b(california|ca)\b",
            "Texas": r"\b(texas|tx)\b",
            "New York": r"\b(new york|ny)\b",
            "Florida": r"\b(florida|fl)\b"
        }

        for state, pattern in state_patterns.items():
            if re.search(pattern, query_lower):
                filters["state_filter"] = state
                break

        if any(kw in query_lower for kw in ["past week", "last week", "last 7 days", "past 7 days"]):
            filters["date_range"] = "past_week"
        elif any(kw in query_lower for kw in ["past month", "last month", "last 30 days"]):
            filters["date_range"] = "past_month"
        elif any(kw in query_lower for kw in ["today", "past 24 hours", "last 24 hours"]):
            filters["date_range"] = "past_24h"

        return filters

    def build_citations(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        citations = []
        for chunk in chunks:
            doc_title = chunk.get("doc_title", "Document")
            page = chunk.get("page", 0)
            paragraph = chunk.get("paragraph", 0)
            label = f"[{doc_title}, p. {page}, par. {paragraph}]"
            citations.append({
                "doc_title": doc_title,
                "page": page,
                "paragraph": paragraph,
                "citation_label": label,
                "snippet": chunk.get("snippet") or chunk.get("text_chunk", "")
            })
        return citations

    def synthesize(self, query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.provider == "fallback":
            self._resolve_provider()

        citations = self.build_citations(chunks)

        if not chunks:
            return {
                "synthesized_answer": "No relevant documents were found matching your query.",
                "llm_provider": self.provider,
                "citations": []
            }


        context_lines = []
        for idx, item in enumerate(citations, 1):
            context_lines.append(f"Source {idx} {item['citation_label']}:\n{item['snippet']}")
        context_str = "\n\n".join(context_lines)

        prompt = (
            f"You are an expert governance assistant. Answer the user question based strictly on the retrieved context below.\n"
            f"Ground your response using citations like [DocTitle, p. X, par. Y].\n\n"
            f"USER QUERY: {query}\n\n"
            f"RETRIEVED CONTEXT:\n{context_str}\n\n"
            f"SYNTHESIZED RESPONSE:"
        )

        answer = None
        used_provider = self.provider

        try:
            if self.provider == "deepseek":
                answer = self._call_deepseek(prompt)
            elif self.provider == "openai":
                answer = self._call_openai(prompt)
            elif self.provider == "claude":
                answer = self._call_claude(prompt)
            elif self.provider == "ollama":
                answer = self._call_ollama(prompt)
        except Exception as exc:
            print(f"Warning: Primary LLM synthesis failed ({self.provider}): {exc}. Falling back to template synthesis.")

        if not answer:
            used_provider = "fallback"
            answer = self._fallback_synthesis(query, citations)

        return {
            "synthesized_answer": answer,
            "llm_provider": used_provider,
            "citations": citations
        }

    def _call_deepseek(self, prompt: str) -> str:
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        raw_model = self.model_name or os.getenv("LLM_MODEL") or "deepseek-chat"
        # DeepSeek API valid models are 'deepseek-chat' and 'deepseek-reasoner'
        if raw_model in ["deepseek-chat", "deepseek-reasoner"]:
            model = raw_model
        else:
            print(f"Notice: Model '{raw_model}' is not a valid DeepSeek API model name. Using 'deepseek-chat'.")
            model = "deepseek-chat"

        api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY")

        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore")
            print(f"DeepSeek API HTTP {http_err.code} Error: {error_body}")
            raise http_err


    def _call_openai(self, prompt: str) -> str:
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        model = self.model_name or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()

    def _call_claude(self, prompt: str) -> str:
        api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        model = self.model_name or "claude-3-5-haiku-20241022"
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        data = json.dumps({
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["content"][0]["text"].strip()

    def _call_ollama(self, prompt: str) -> str:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = self.model_name or os.getenv("OLLAMA_MODEL", "llama3")
        url = f"{base_url.rstrip('/')}/api/generate"
        headers = {"Content-Type": "application/json"}
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "").strip()

    def _fallback_synthesis(self, query: str, citations: List[Dict[str, Any]]) -> str:
        bullets = []
        for c in citations[:3]:
            snippet_clean = c['snippet'].replace("\n", " ")
            bullets.append(f"- {c['citation_label']}: \"{snippet_clean}\"")
        bullet_str = "\n".join(bullets)
        return (
            f"Based on your query '{query}', here are key relevant findings from retrieved governance documents:\n\n"
            f"{bullet_str}\n\n"
            f"Refer to the citations above for full document contexts."
        )
