from datetime import datetime, timezone
import os
import json
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from openai import AsyncAzureOpenAI
from langsmith import traceable, tracing_context, wrappers

from app.schemas.ChatSession import ChatSessionTitle
from app.helpers.VectorDB import VectorDB
from app.schemas.ProactiveMessage import ProactiveMessages

from typing import Any, Dict, List, Optional

from app.helpers.SERP import SERPHelper

load_dotenv()


SYSTEM_PROMPT_TEMPLATE = """You are an AI assistant specialized in HR laws, compliance, and court decisions.

# Context
- Current Unix timestamp: {current_ts}
- Interpret all relative dates (e.g., "today", "this year", "after July 2024") against this timestamp.

# Knowledge & Tools
You have:
- Curated HR/legal knowledge in a vector DB (Pinecone) with metadata fields:
  location_slug, primary_industry_slug, secondary_industry_slug, region_slug, topic_slug, discussedTimestamp
- Slug vector stores for resolving fuzzy user text into canonical slugs
- A SERP tool for fresh results when curated data is insufficient
- A web content fetcher to extract clean text from URLs

# Decision Flow
1) If the query contains fuzzy location/topic/industry/region → call resolve_filter_slug with all required queries at once.
2) Query curated store → search_documents (prioritize this).
   - MANDATORY: Before using any filters in search_documents, you MUST first get the correct filter values from resolve_filter_slug.
   - Only use filters if you have valid slugs from resolve_filter_slug - never invent or guess filter values.
   - When user implies time: use discussedTimestamp_gt/lt only.
3) If results are missing/stale or user asks for "latest" → fetch_serp_content, then get_webpage_content for ONLY the most relevant URL.
4) Summarize clearly, cite sources (pageUrl/file_url/file_name/source), cluster by topic/date.

- Never invent slugs; always normalize via resolve_filter_slug.
"""



def _tool_schemas():
    """Return OpenAI tool schemas for function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "resolve_filter_slug",
                "description": "Resolve natural language into a metadata slug via vector search. Can resolve multiple queries at once.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["location", "primary_industry", "secondary_industry", "topic", "region"]
                                    },
                                    "query": {"type": "string"}
                                },
                                "required": ["type", "query"]
                            },
                            "description": "Array of queries to resolve. Each query should have a type and query string."
                        }
                    },
                    "required": ["queries"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_documents",
                "description": "Search HR law documents in Pinecone with semantic query and metadata filters.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "filters": {
                            "type": "object",
                            "properties": {
                                "location_slug": {"type": "string"},
                                "primary_industry_slug": {"type": "string"},
                                "secondary_industry_slug": {"type": "string"},
                                "region_slug": {"type": "string"},
                                "topic_slug": {"type": "string"},
                                "sourceType": {"type": "string"},
                                "discussedTimestamp_gt": {"type": "number"},
                                "discussedTimestamp_lt": {"type": "number"}
                            }
                        },
                        "top_k": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_serp_content",
                "description": "Fetch latest HR/legal resources from the web via SERP API.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "num_results": {"type": "integer", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_webpage_content",
                "description": "Scrape and clean webpage content from a given URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"}
                    },
                    "required": ["url"]
                }
            }
        }
    ]


class AIChat:
    def __init__(self, namespace):
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()]
        )

        self.client = wrappers.wrap_openai(AsyncAzureOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
        ))

        self.vector_database = VectorDB(namespace)
        
        # Create vector DB helpers
        self.locations_slug_vector_db_helper = VectorDB("LocationsSlug")
        self.primary_industry_slug_vector_db_helper = VectorDB("PrimaryIndustrySlug")
        self.secondary_industry_slug_vector_db_helper = VectorDB("SecondaryIndustrySlug")
        self.topics_slug_vector_db_helper = VectorDB("TopicSlug")
        self.regions_slug_vector_db_helper = VectorDB("RegionsSlug")

        # Create retrievers for each namespace
        self.locations_slug_retriever = self.locations_slug_vector_db_helper.get_vector_retriever()
        self.primary_industry_slug_retriever = self.primary_industry_slug_vector_db_helper.get_vector_retriever()
        self.secondary_industry_slug_retriever = self.secondary_industry_slug_vector_db_helper.get_vector_retriever()
        self.topics_slug_retriever = self.topics_slug_vector_db_helper.get_vector_retriever()
        self.regions_slug_retriever = self.regions_slug_vector_db_helper.get_vector_retriever()
        
        self.serp_helper = SERPHelper()
        

    @traceable(name="azure-openai-tool-call")
    async def _openai_tool_call(self, messages, tools, metadata=None):
        with tracing_context(tags=["tool-call"], metadata=metadata or {}):
            return await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                stream=False
            )

    @traceable(name="azure-openai-stream")
    async def _openai_stream_response(self, messages, metadata=None):
        with tracing_context(tags=["stream-final-answer"], metadata=metadata or {}):
            return await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )

    # -----------------------------
    # TOOL IMPLEMENTATION STUBS
    # -----------------------------
    
    # --------- helpers ---------

    # --------- tool handler ---------
    async def _tool_resolve_filter_slug(self, args: dict) -> dict:
        """
        INPUT: {"queries": [{"type": "location|primary_industry|secondary_industry|topic|region", "query": "..."}, ...]}
        OUTPUT: {"results": [{"type": "location", "query": "california", "slug": "california"}, ...]}

        Uses the requested retriever for each query, runs a query, picks the FIRST result.
        """
        try:
            queries = args.get("queries", [])
            if not queries:
                return {"results": [], "error": "No queries provided"}

            results = []
            
            for query_item in queries:
                query_type = query_item.get("type")
                query = (query_item.get("query") or "").strip()
                
                if not query:
                    results.append({
                        "type": query_type,
                        "query": query,
                        "slug": None,
                        "error": "Empty query"
                    })
                    continue

                # Switch-case style (Python 3.10+)
                match query_type:
                    case "location":
                        retriever = self.locations_slug_retriever
                    case "primary_industry":
                        retriever = self.primary_industry_slug_retriever
                    case "secondary_industry":
                        retriever = self.secondary_industry_slug_retriever
                    case "topic":
                        retriever = self.topics_slug_retriever
                    case "region":
                        retriever = self.regions_slug_retriever
                    case _:
                        results.append({
                            "type": query_type,
                            "query": query,
                            "slug": None,
                            "error": f"Unsupported type: {query_type}"
                        })
                        continue

                # Direct invoke
                retriever_results = retriever.invoke(query) if hasattr(retriever, "invoke") else []
                if not retriever_results:
                    results.append({
                        "type": query_type,
                        "query": query,
                        "slug": None
                    })
                else:
                    # Pick the first doc only
                    first = retriever_results[0]
                    slug = first.page_content
                    results.append({
                        "type": query_type,
                        "query": query,
                        "slug": slug
                    })

            return {"results": results}

        except Exception as e:
            return {"results": [], "error": f"An error occurred: {str(e)}"}



    def _format_filters_for_pinecone(self,filters: dict) -> dict:
        """
        Convert filters with _gt / _lt keys into Pinecone-compatible operators.
        Example input:
            {
                "location_slug": "california",
                "topic_slug": "labor-employment",
                "discussedTimestamp_gt": 1700000000,
                "discussedTimestamp_lt": 1800000000
            }
        Output:
            {
                "location_slug": {"$eq": "california"},
                "topic_slug": {"$eq": "labor-employment"},
                "discussedTimestamp": {"$gt": 1700000000, "$lt": 1800000000}
            }
        """
        pinecone_filters = {}
        for key, value in (filters or {}).items():
            if key.endswith("_gt"):
                field = key.replace("_gt", "")
                pinecone_filters.setdefault(field, {})["$gt"] = value
            elif key.endswith("_lt"):
                field = key.replace("_lt", "")
                pinecone_filters.setdefault(field, {})["$lt"] = value
            else:
                pinecone_filters[key] = {"$eq": value}
        return pinecone_filters


    async def _tool_search_documents(self, args: dict) -> dict:
        """
        INPUT:
          {
            "query": "...",
            "filters": {...},
            "top_k": 10
          }
        OUTPUT (example):
          {
            "docs": [
              {
                "content": "...",
                "metadata": {
                  "pageUrl": "...",
                  "file_url": "...",
                  "file_name": "...",
                  "source": "HR Resource",
                  "ingestion_date": "...",
                  "discussedTimestamp": 1721260800
                }
              },
              ...
            ]
          }
        """
        
        try:
            query = args.get("query")
            filters = self._format_filters_for_pinecone(args.get("filters"))
            top_k = args.get("top_k", 10)
            
            # Retrieve top 5 docs without any filters
            docs_without_filter = self.vector_database.retrieve_by_metadata(query, {}, 5)

            # Retrieve top_k docs with filters
            docs = self.vector_database.retrieve_by_metadata(query, filters, top_k)
            
            # Merge lists properly
            docs.extend(docs_without_filter)

            return {"docs": [doc.model_dump() for doc in docs]}

        except Exception as e:
            return {"error": f"An error occurred:"}

        
    async def _tool_fetch_serp_content(self, args: dict) -> dict:
        """
        INPUT: {"query": "...", "num_results": 5}
        OUTPUT (example): {"results": [{"title":"...","url":"..."}, ...]}
        """
        try:
            search_query = args.get("query", "")
            num_results = int(args.get("num_results", 5))

            serp_data = self.serp_helper.serp_results(search_query)

            return {"results": serp_data[:num_results]}

        except Exception as e:
            return {"error": f"An error occurred"}

        
        

    async def _tool_get_webpage_content(self, args: dict) -> dict:
        """
        INPUT: {"url": "..."}
        OUTPUT (example):
          {
            "url": "...",
            "title": "...",
            "content": "cleaned page text or markdown"
          }
        """
        
        try:
            url  = args.get("url","")
            page_data = self.serp_helper.get_webpage(url)
            return {"content":page_data }
        
        except Exception as e:
            return {"error": f"An error occurred"}
            
        

    # -----------------------------
    # ROUTER FOR TOOL CALLS
    # -----------------------------
    async def _dispatch_tool(self, name: str, arguments_json: str) -> dict:
        args = json.loads(arguments_json or "{}")
        if name == "resolve_filter_slug":
            return await self._tool_resolve_filter_slug(args)
        if name == "search_documents":
            return await self._tool_search_documents(args)
        if name == "fetch_serp_content":
            return await self._tool_fetch_serp_content(args)
        if name == "get_webpage_content":
            return await self._tool_get_webpage_content(args)
        return {}

    def _collect_citations_from_docs(self, docs: list) -> list:
        """
        Deduplicate and shape citations array from list of doc dicts.
        """
        citations, seen = [], set()
        for d in docs:
            md = d.get("metadata", {}) if isinstance(d, dict) else getattr(d, "metadata", {})
            citation_obj = {}
            for k in ["file_url", "file_name", "pageUrl", "source"]:
                v = md.get(k)
                if v:
                    citation_obj[k] = v
            if citation_obj:
                key = (
                    citation_obj.get("file_url"),
                    citation_obj.get("file_name"),
                    citation_obj.get("pageUrl"),
                    citation_obj.get("source"),
                )
                if key not in seen:
                    seen.add(key)
                    citations.append(citation_obj)
        return citations
    
        # --- helpers for recursive tool calling ---

    def _accumulate_context_from_tool_result(self, tool_name: str, tool_result: dict, aggregated_context: str, all_citations: list):
        """
        Consolidate docs/page content into a single reference context string and dedupe citations.
        """
        # Collect docs (vector results)
        docs = tool_result.get("docs") if isinstance(tool_result, dict) else None
        if docs:
            all_citations.extend(self._collect_citations_from_docs(docs))
            for d in docs:
                content = d.get("content", "")
                md = d.get("metadata", {})
                ingestion_date = md.get("ingestion_date", "")
                aggregated_context += f"{content}\nCreated On: {ingestion_date}\n\n"

        # Collect cleaned webpage text (scraped content)
        page_text = tool_result.get("content") if isinstance(tool_result, dict) else None
        if page_text:
            aggregated_context += f"{page_text}\n\n"

        return aggregated_context, all_citations

    async def _run_tools_recursive(self, chat_history: list, tools: list, meta: dict, max_rounds: int = 50, max_calls_per_round: int = 50):
        """
        Recursive(ish) tool runner: repeatedly asks the model if it wants to call tools.
        Returns (final_messages, aggregated_context, citations)
        """
        aggregated_context = ""
        all_citations = []

        for round_idx in range(max_rounds):
            # Ask model: do you want to call a tool?
            response = await self._openai_tool_call(
                chat_history,
                tools,
                metadata={**meta, "tool_round": round_idx + 1}
            )
            message = response.choices[0].message

            # If no tool calls, we’re done — return final message context to stream
            if not getattr(message, "tool_calls", None):
                # push the assistant message (content) into history for continuity
                if getattr(message, "content", None):
                    chat_history.append({"role": "assistant", "content": message.content})
                return chat_history, aggregated_context, all_citations

            # Add an assistant message that records all tool_calls
            assistant_tool_msg = {
                "role": "assistant",
                "content": "",
                "tool_calls": [tc.to_dict() if hasattr(tc, "to_dict") else vars(tc) for tc in message.tool_calls]
            }
            chat_history.append(assistant_tool_msg)

            # Dispatch each tool call (bounded)
            for call_idx, tool_call in enumerate(message.tool_calls[:max_calls_per_round]):
                tool_name = tool_call.function.name
                tool_args_json = tool_call.function.arguments

                # Execute the tool
                tool_result = await self._dispatch_tool(tool_name, tool_args_json)

                # Update context & citations
                aggregated_context, all_citations = self._accumulate_context_from_tool_result(
                    tool_name, tool_result, aggregated_context, all_citations
                )

                # Push tool result back to the model
                chat_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            # loop continues → model now sees tool outputs and may request further tools

        # safety exit: too many rounds
        chat_history.append({
            "role": "assistant",
            "content": "Stopping tool calls due to safety limit. Summarizing available findings."
        })
        return chat_history, aggregated_context, all_citations

    # --- main entrypoint, now recursive ---
    async def chat_with_knowledge_stream_openai_tools(self, question, session):
        """
        Orchestrates:
          - System prompt with current timestamp
          - Recursive multi-tool function calling (multiple rounds until no tool calls)
          - Streams final answer with citations
        """
        try:
            from datetime import timezone
            current_ts = int(datetime.now(timezone.utc).timestamp())

            system_message = {
                "role": "system",
                "content": SYSTEM_PROMPT_TEMPLATE.format(current_ts=current_ts)
            }

            # 1) assemble history (system + prior)
            chat_history = [system_message]
            for message in session.get("messages", []):
                if message["messageType"] == "user":
                    chat_history.append({"role": "user", "content": message["message"]})
                elif message["messageType"] == "assistant":
                    chat_history.append({"role": "assistant", "content": message["message"]})

            # 2) current user turn
            chat_history.append({"role": "user", "content": question})

            tools = _tool_schemas()
            meta = {
                "question": question,
                "session_id": session.get("sessionId"),
                "current_ts": current_ts
            }

            # 3) Run recursive tool loop
            chat_history_after_tools, aggregated_context, all_citations = await self._run_tools_recursive(
                chat_history, tools, meta, max_rounds=4, max_calls_per_round=6
            )

            # 4) Final streaming answer (no more tool calls)
            stream = await self._openai_stream_response(
                chat_history_after_tools,
                metadata={
                    **meta,
                    "citations": all_citations,
                    "reference_context": aggregated_context,
                    "tool_used": True
                }
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "content": chunk.choices[0].delta.content,
                        "citations": all_citations,
                        "tool_output": aggregated_context
                    }
            return

        except Exception as e:
            print(str(e))
            yield None

   
    def get_chat_session_title(self, question: str, answer: str) -> ChatSessionTitle:
        structured_llm = self.chat.with_structured_output(ChatSessionTitle)
        final_resp = structured_llm.invoke(
            f"Extract meaningful chat session title from this conversation:\nQuestion: {question}\nAnswer: {answer}"
        )
        return final_resp

    def generateProactiveMessages(self, conversationHistory, dashboard_info):
        system_message = SystemMessage(
            content=f"""Your task: The user dropped off from a conversation.

Analyze the last few messages from the user **along with their dashboard preferences**, and generate **5 unique proactive follow-up messages** the user might initiate — written from the **user’s perspective**.

The user's selected filters:
- Industries: {", ".join(dashboard_info.get("industries", []))}
- Topics: {", ".join(dashboard_info.get("topics", []))}
- Locations: {", ".join(dashboard_info.get("locations", []))}

### Guidelines:
- Each message must sound like it’s written by the **user**.
- Keep each message **under 10 words**.
- **Naturally embed** the jurisdiction (location), topic, and industry.
- Vary the **intent**.
- Vary sentence structure across the 5 messages.
- Professional but conversational. Avoid robotic phrasing.
- Do not mention that the user dropped off.
"""
        )
        messages = [
            system_message,
            HumanMessage(content=f"Generate the 5 follow-up messages for this conversation history: {conversationHistory}")
        ]
        structured_llm = self.chat.with_structured_output(ProactiveMessages)
        response = structured_llm.invoke(messages)
        return response

    def extract_messages_from_last_system(self, conversation_):
        if not conversation_:
            return []

        conversation = [d.to_dict() if hasattr(d, 'to_dict') else d for d in conversation_]
        if not conversation:
            return []

        last_n_messages = conversation[-15:]
        last_n_messages = [
            msg for msg in last_n_messages
            if msg.get("role") not in ["system", "tool"] and not msg.get("tool_calls")
        ]

        cleaned_messages = []
        for msg in last_n_messages:
            temp = msg.copy()
            for field in ["sentiment", "feedback", "_id", "createdAt", "updatedAt"]:
                temp.pop(field, None)
            if temp.get("tool_calls") == []:
                temp.pop("tool_calls", None)
            cleaned_messages.append(temp)

        return cleaned_messages
