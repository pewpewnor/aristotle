import json
import operator
import os
from typing import Annotated, List, Optional, Tuple, TypedDict

from langchain_core.messages import (AIMessage, BaseMessage, HumanMessage,
                                     SystemMessage)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from aristotle import project_config
from aristotle.agent.loaded_codebases import list_all_codebases
from server.request_types import ChatHistoryItem, FileContent

from .load_tools import CodebaseLoaderTool, ListLoadedCodebases
from .search_tools import CombinedSearchTool, EntityRelationshipSearchTool


class ResponseFormat(BaseModel):
    response: str = Field(description="Detailed answer or explanation in markdown")
    references: List[str] = Field(
        default_factory=list, description="List of references used"
    )


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    structured_response: Optional[ResponseFormat]
    retry_count: int
    tool_calls: int


if os.path.isfile(project_config.system_prompt_file):
    with open(project_config.system_prompt_file) as f:
        system_prompt = f.read().strip()
else:
    system_prompt = """You are Aristotle, an expert codebase analysis assistant.

Answer questions about loaded codebases with accurate, sourced information. Search through code to find relevant implementations, documentation, and examples.

## Tools

**search** - Find information in codebases
- Use for: questions about code, APIs, classes, functions, architecture, examples
- Always include codebase name in query
- Make the query more specific and detailed to get better results
- Always include the name of provided class, function, field, etc given by the user in the query.
- Perform multiple searches if needed for complete answers
- Example: "Pandas DataFrame to_json method have what parameters"

**load_codebase** - Add new codebases
- Accepts Git URLs (e.g. https://github.com/user/repo) or PyPI packages (Python package name)
- Prefer PyPI package names when user doesn't specify Git URL

## Workflow

**Information queries:**
1. Search with relevant keywords + codebase name
2. Perform additional searches if needed
3. Synthesize findings with references

**Loading requests:**
1. load_codebase only if not already loaded
2. Only use if the codebase is not already on previous list of loaded codebases
3. Confirm status

## Response Standards
- Use markdown formatting with code blocks
- Cite specific files/functions when available and absolutely relevant
- Distinguish codebase info from general knowledge
- Acknowledge when searches don't find relevant info
- Filter irrelevant results

CRITICAL REMINDERS:
- User asks question → use search at least once, always include codebase name in the query
- User wants to load codebase → see list loaded codebases first, then load_codebase if needed
- Never include tool names in responses
"""


class AristotleAgent:
    def __init__(
        self,
        base_url: str = project_config.ollama_base_url,
        model: str = project_config.ollama_llm_main_model,
        temperature: float = project_config.llm_temperature,
        max_retries: int = 3,
        max_tool_calls: int = 3,
    ) -> None:
        self.llm = ChatOllama(model=model, temperature=temperature, base_url=base_url)
        print("[INFO] Using normal toolset")
        self.tools: List[BaseTool] = [
            CombinedSearchTool(),
            ListLoadedCodebases(),
            CodebaseLoaderTool(),
            # EntityRelationshipSearchTool(),
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.llm_structured = ChatOllama(
            model=model, temperature=temperature, format="json", base_url=base_url
        )
        self.max_retries = max_retries
        self.max_tool_calls = max_tool_calls
        self.graph = self.build_graph()

    def build_graph(self) -> CompiledStateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("respond", self.structured_response)

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "respond": "respond",
            },
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("respond", END)

        return workflow.compile()

    def convert_history_to_messages(
        self, chat_history: List[ChatHistoryItem]
    ) -> List[BaseMessage]:
        messages = []
        for item in chat_history:
            if item.type == "HUMAN_MESSAGE":
                messages.append(HumanMessage(content=item.content))
            elif item.type == "AI_MESSAGE":
                messages.append(AIMessage(content=item.content))
        return messages

    async def call_model(self, state: AgentState) -> dict:
        messages = state["messages"]
        tool_call_count = state.get("tool_call_count", 0)

        has_system = any(isinstance(m, SystemMessage) for m in messages)
        if not has_system:
            messages = [SystemMessage(content=system_prompt)] + messages

        response = await self.llm_with_tools.ainvoke(messages)

        new_tool_count = tool_call_count
        if (
            isinstance(response, AIMessage)
            and hasattr(response, "tool_calls")
            and response.tool_calls
        ):
            new_tool_count = tool_call_count + len(response.tool_calls)

        return {"messages": [response], "tool_call_count": new_tool_count}

    def should_continue(self, state: AgentState) -> str:
        messages = state["messages"]
        last_message = messages[-1]
        tool_call_count = state.get("tool_call_count", 0)

        if tool_call_count >= self.max_tool_calls:
            print(
                f"[WARNING] Max tool calls ({self.max_tool_calls}) reached, moving to respond"
            )
            return "respond"
        if (
            isinstance(last_message, AIMessage)
            and hasattr(last_message, "tool_calls")
            and last_message.tool_calls
        ):
            return "continue"
        return "respond"

    async def structured_response(self, state: AgentState) -> dict:
        messages = state["messages"]
        retry_count = state.get("retry_count", 0)

        structured_prompt = f"""Based on the conversation history, provide a final response in the following JSON format:
{{
    "response": "Your detailed answer or explanation as a string in markdown content",
    "references": ["list of references or sources used"]
}}

Conversation context:
{self.format_messages_for_context(messages)}

Remember to:
1. Include all relevant information gathered from the tools
2. Format your response in markdown
3. List any references or sources
4. Provide a comprehensive answer to the user's question
5. Never include tool names in response or references

You MUST respond with valid JSON only. Do not include any text outside the JSON object."""

        try:
            response = await self.llm_structured.ainvoke([("user", structured_prompt)])

            content = response.content
            if isinstance(content, list):
                content = content[0] if content else "{}"
            if isinstance(content, dict):
                content = json.dumps(content)

            parsed = json.loads(content)

            if not isinstance(parsed, dict) or "response" not in parsed:
                raise ValueError("Invalid response format: missing 'response' field")

            structured = ResponseFormat(**parsed)

            return {
                "structured_response": structured,
                "messages": [AIMessage(content=structured.response)],
                "retry_count": 0,
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if retry_count < self.max_retries:
                print(
                    f"[RETRY {retry_count + 1}/{self.max_retries}] Format error: {str(e)}"
                )
                retry_prompt = f"""Your previous JSON response was invalid. Error: {str(e)}

Please provide a valid JSON response in this EXACT format:
{{
    "response": "Your detailed answer in markdown",
    "references": ["list of references"]
}}

Context:
{self.format_messages_for_context(messages)}

Respond with ONLY valid JSON, no other text."""

                try:
                    retry_response = await self.llm_structured.ainvoke([("user", retry_prompt)])
                    retry_content = retry_response.content
                    if isinstance(retry_content, list):
                        retry_content = retry_content[0] if retry_content else "{}"
                    if isinstance(retry_content, dict):
                        retry_content = json.dumps(retry_content)
                    
                    retry_parsed = json.loads(retry_content)
                    if not isinstance(retry_parsed, dict) or "response" not in retry_parsed:
                        raise ValueError("Invalid retry response format")
                    
                    structured = ResponseFormat(**retry_parsed)
                    return {
                        "structured_response": structured,
                        "messages": [AIMessage(content=structured.response)],
                        "retry_count": 0,
                    }
                except Exception as retry_error:
                    print(f"[RETRY ERROR] {str(retry_error)}")
                    return {
                        "retry_count": retry_count + 1,
                        "messages": messages,
                    }
            else:
                print(f"[ERROR] Max retries exceeded: {str(e)}")
                fallback = ResponseFormat(
                    response="I apologize, but I encountered an error while formatting the response. Please try rephrasing your question.",
                    references=[],
                )
                return {
                    "structured_response": fallback,
                    "messages": [AIMessage(content=fallback.response)],
                    "retry_count": 0,
                }
        except Exception as e:
            print(f"[ERROR] Unexpected error in structured_response: {str(e)}")
            fallback = ResponseFormat(
                response="An unexpected error occurred while processing your request. Please try again.",
                references=[],
            )
            return {
                "structured_response": fallback,
                "messages": [AIMessage(content=fallback.response)],
                "retry_count": 0,
            } 

    def format_messages_for_context(self, messages: List[BaseMessage]) -> str:
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    formatted.append(
                        f"Assistant: [Called tools: {[tc['name'] for tc in msg.tool_calls]}]"
                    )
                else:
                    formatted.append(f"Assistant: {msg.content}")
        return "\n".join(formatted)

    async def chat(
        self,
        prompt: str,
        chat_history: Optional[List[ChatHistoryItem]] = None,
        files: Optional[List[FileContent]] = None,
    ) -> Tuple[Optional[ResponseFormat], Optional[str]]:
        try:
            messages = []
            if chat_history:
                messages.extend(self.convert_history_to_messages(chat_history))
            message_suffix = ""
            if files:
                message_suffix += "\n\nAttached files for this message:\n" + json.dumps(
                    [file.model_dump() for file in files]
                )
            messages.append(
                SystemMessage(
                    content="Loaded codebases status, do not load codebases that are already 'LOADED' or 'IN_PROGRESS':\n"
                    + list_all_codebases()
                )
            )
            messages.append(HumanMessage(content=prompt + message_suffix))

            result = await self.graph.ainvoke(
                {"messages": messages, "retry_count": 0}, config=RunnableConfig()
            )

            structured = result.get("structured_response")
            if structured:
                return structured, None
            else:
                return None, "No structured response generated"
        except Exception as e:
            error_msg = f"Error during chat: {str(e)}"
            print("[ERROR]", error_msg)
            return None, error_msg
