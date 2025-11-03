import json
import os
import random
import threading
from typing import Any, Dict, List
from dotenv import load_dotenv
import time
from datetime import datetime, timezone
from langchain_openai import OpenAIEmbeddings
from openai import AzureOpenAI
from pinecone import Pinecone, ServerlessSpec, Index
from pinecone.exceptions import NotFoundException
from app.helpers.Utilities import Utils
from app.helpers.VectorDB import VectorDB
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from uuid import uuid4
from langchain_core.documents import Document
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage,AIMessage
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from app.schemas.ChatSession import ChatSessionTitle
from app.helpers.SERP import SERPHelper
from app.helpers.PdfGenerator import PdfGenerator


from dotenv import load_dotenv

load_dotenv()

class AIChatNoStream:
    def __init__(self, namespace):
        # self.chat = ChatOpenAI(
        #     api_key=os.getenv('OPENAI_API'),
        #     temperature=0.5,
        #     model='gpt-4o-mini'
        # )
        
        
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )
        
        self.azure_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.vector_database = VectorDB(namespace)
        self.vector_retriever = self.vector_database.get_vector_retriever()
        
        self.types_vector_database = VectorDB(f"{namespace}-TYPES")
        self.types_vector_retriever = self.types_vector_database.get_vector_retriever()
        
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
        self.pdf_generator_helper=PdfGenerator()
        
        


    def chat_with_knowledge(self, question, session,persona):
        try:
            docs = self.vector_retriever.invoke(question)
            docs_as_string = ''
            sources = set()
            for doc in docs:
                docs_as_string += f"{doc.page_content} \n Created On: {doc.metadata.get('ingestion_date')} \n\n"
                source_custom = doc.metadata.get('file_name')
                source_default = doc.metadata.get('source')
                if(source_custom):
                    sources.add(source_custom)
                elif(source_default):
                    sources.add(source_default)
                
            system_message=persona.get('SystemPrompt')
            if(not system_message):
                system_message = """You are a helpful assistant capable of answering questions and engaging in casual conversation. 
                    You should answer the question based on the context: 
                    Each context has a timestamp called 'Created On' at the end.
                    If there are similar contexts, then based on the timestamp answer the question with the most recent context."""

            system_message = SystemMessage(
                content=f"""{system_message}
                
                Context: {docs_as_string}
                
                
                """
            )
            chat_history = [system_message]
            for message in session.get("Messages", []):
                if message["MessageType"] == "user":
                    chat_history.append(HumanMessage(content=message["Message"]))
                elif message["MessageType"] == "assistant":
                    chat_history.append(AIMessage(content=message["Message"]))
            chat_history.append(HumanMessage(content=question))
            response = self.chat.invoke(chat_history)
            # print("length of chat_history",len(chat_history))
            # print(list(sources))
            return response.content,list(sources)

        except Exception as e:
            print(str(e))
            return None

    def get_chat_session_title(self,question: str, answer:str) -> ChatSessionTitle:
        
        structured_llm = self.chat.with_structured_output(ChatSessionTitle)

        final_resp = structured_llm.invoke(f"Extract meaningful chat session title from this conversation from the following conversation:\nQuestion: {question}\nAnswer: {answer}")
        return final_resp
    
    def chat_with_tools(self, input_messages,user_question,persona = None):
        try:
            user_message = {
                "role":"user",
                "content":user_question,
                "timestamp":datetime.now(timezone.utc)
                
            }
            input_messages.setdefault("messages", []).append(user_message)
            llm_history = self.format_messages(input_messages,persona)
            
            tools = [
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
                                "description": "Search HR law documents in Pinecone with semantic query and metadata filters. Use higher top_k values (15-20) for comprehensive research.",
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
                                        "top_k": {"type": "integer", "default": 15, "description": "Number of results to retrieve. Use 15-20 for comprehensive research."}
                                    },
                                    "required": ["query"]
                                }
                            }
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "fetch_serp_content",
                                "description": "Fetch latest HR/legal resources from the web via SERP API. Use higher num_results (8-10) for comprehensive research.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "num_results": {"type": "integer", "default": 8, "description": "Number of search results to fetch. Use 8-10 for thorough research."}
                                    },
                                    "required": ["query"]
                                }
                            }
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "get_webpage_content",
                                "description": "Scrape and clean webpage content from one or more URLs in parallel. Use 'urls' for multiple URLs or 'url' for single URL.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "urls": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Array of URLs to scrape content from (preferred for multiple URLs)"
                                        },
                                        "url": {
                                            "type": "string",
                                            "description": "Single URL to scrape (alternative to urls array)"
                                        }
                                    }
                                }
                            }
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "generate_pdf",
                                "description": "Generate a downloadable PDF from raw content",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "Title of the PDF"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Raw content to be included in the PDF"
                                        },
                                        "page_size": {
                                            "type": "string",
                                            "description": "PDF page size (e.g., 'A4 portrait')",
                                            "default": "A4 portrait"
                                        }
                                    },
                                    "required": ["title", "content"]
                                }
                            }
                        }
                    ]

            response = self.azure_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=llm_history,
                    tools=tools,
                )
            
            citations = set()
            
            response_message = response.choices[0].message
            message_content = response.choices[0].message.content
            
            # print(f"Initial response - content: '{message_content}'")
            # print(f"Initial response - tool_calls: {getattr(response_message, 'tool_calls', None)}")
                
            tool_call_responses = []
            
            # Stream the initial response if it has content (no tool calls)
            if message_content:
                    yield message_content
            
            # Process tool calls if present
            # print(f"Checking tool calls - message_content: '{message_content}', has_tool_calls: {hasattr(response_message, 'tool_calls')}, tool_calls: {getattr(response_message, 'tool_calls', None)}")
            while not message_content and hasattr(response_message, 'tool_calls') and response_message.tool_calls and len(response_message.tool_calls) > 0:
                for tool_call in response_message.tool_calls:
                    
                    # Convert tool call to dictionary format
                    tool_call_dict = {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    tool_call_response = {"role": "assistant","tool_calls": [tool_call_dict]}
                    
                    llm_history.append(tool_call_response)
                    
                    input_messages.setdefault("messages", []).append(tool_call_response)

                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    result,citations_ = self.call_function(name, args)
                    citations.update(citations_)
                    tool_call_responses.append(result)
                    
                    input_messages.setdefault("messages", []).append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content": json.dumps(result) ,
                    })
                    
                    llm_history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_call.function.name,
                        "content":json.dumps(result),
                    })
                
                # Get the next streaming response after processing all tool calls
                # print("Starting streaming response after tool calls...")
                with self.azure_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=llm_history,
                    tools=tools,
                    stream=True
                ) as stream:
                    
                    message_content = ""
                    response_message = None
                    
                    for event in stream:
                        if not event.choices:
                            continue
                        
                        delta = event.choices[0].delta
                        
                        # Handle text content streaming
                        if hasattr(delta, "content") and delta.content:
                            chunk_text = delta.content
                            message_content += chunk_text
                            # print(f"Streaming chunk: '{chunk_text}'")  # Debug
                            yield chunk_text
                        
                        # Handle tool calls in streaming response
                        if hasattr(delta, "tool_calls") and delta.tool_calls:
                            if response_message is None:
                                response_message = type("Obj", (), {"tool_calls": []})()
                            
                            for delta_tool_call in delta.tool_calls:
                                # Initialize new tool call if needed
                                if delta_tool_call.index >= len(response_message.tool_calls):
                                    response_message.tool_calls.extend([None] * (delta_tool_call.index + 1 - len(response_message.tool_calls)))
                                
                                if response_message.tool_calls[delta_tool_call.index] is None:
                                    response_message.tool_calls[delta_tool_call.index] = {
                                        "id": delta_tool_call.id,
                                        "type": "function",
                                        "function": {
                                            "name": delta_tool_call.function.name,
                                            "arguments": ""
                                        }
                                    }
                                
                                # Accumulate function arguments
                                if delta_tool_call.function.arguments:
                                    response_message.tool_calls[delta_tool_call.index]["function"]["arguments"] += delta_tool_call.function.arguments
                    
                    # Update response_message for potential additional tool calls
                    if response_message and hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                        # Convert streaming tool calls to proper format that matches Azure response structure
                        tool_calls_list = []
                        for tc in response_message.tool_calls:
                            if tc is not None:
                                # Create objects that match the Azure response structure
                                function_obj = type("Function", (), {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"]
                                })()
                                tool_call_obj = type("ToolCall", (), {
                                    "id": tc["id"],
                                    "function": function_obj
                                })()
                                tool_calls_list.append(tool_call_obj)
                        response_message = type("ResponseMessage", (), {
                            "tool_calls": tool_calls_list,
                            "content": None
                        })()
                    else:
                        response_message = type("ResponseMessage", (), {"content": message_content, "tool_calls": None})()
                
            input_messages.setdefault("messages", []).append({
                "role": "assistant",
                "content": message_content,
                "tool_calls": self.remove_duplicates(tool_call_responses),
                "timestamp": datetime.now(timezone.utc)
            })

            # print(f"Final yield - history: {len(input_messages.get('messages', []))} messages, citations: {len(citations)}")
            
            # If no content was generated, yield a test message
            if not message_content:
                # print("No content generated, yielding test message")
                yield "Test message: No content was generated by the AI."
            
            yield {"history": input_messages, "citations": list(citations)}

        except Exception as e:
            # print("Error in chat with RAG Chat", str(e))
            yield {"error": str(e)}

    def call_function(self, name, args):
        if name == "resolve_filter_slug":
            return self._tool_resolve_filter_slug(args), []
        elif name == "search_documents":
            return self._tool_search_documents(args), []
        elif name == "fetch_serp_content":
            return self._tool_fetch_serp_content(args), []
        elif name == "get_webpage_content":
            return self._tool_get_webpage_content(args), []
        elif name == "generate_pdf":
            return self._tool_generate_pdf(args), []
        else:
            return {"error": f"Unknown function: {name}"}, []


    def _tool_resolve_filter_slug(self, args: dict) -> dict:
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


    def _tool_search_documents(self, args: dict) -> dict:
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
            top_k = args.get("top_k", 15)
            
            # Retrieve top 10 docs without any filters for broader context
            docs_without_filter = self.vector_database.retrieve_by_metadata(query, {}, 10)

            # Retrieve top_k docs with filters
            docs = self.vector_database.retrieve_by_metadata(query, filters, top_k)
            
            # Merge lists and remove duplicates
            all_docs = docs + docs_without_filter
            seen_ids = set()
            docs = []
            for doc in all_docs:
                doc_id = doc.metadata.get('id', doc.page_content[:50])  # Use ID or first 50 chars as identifier
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    docs.append(doc)

            return {"docs": [doc.model_dump() for doc in docs]}

        except Exception as e:
            return {"error": f"An error occurred:"}

        
    def _tool_fetch_serp_content(self, args: dict) -> dict:
        """
        INPUT: {"query": "...", "num_results": 8}
        OUTPUT (example): {"results": [{"title":"...","url":"..."}, ...]}
        """
        try:
            search_query = args.get("query", "")
            num_results = int(args.get("num_results", 8))

            serp_data = self.serp_helper.serp_results(search_query)

            return {"results": serp_data[:num_results]}

        except Exception as e:
            return {"error": f"An error occurred"}

        
        

    def _tool_get_webpage_content(self, args: dict) -> dict:
        """
        INPUT: {"url": "..."} or {"urls": ["...", "..."]} or both
        OUTPUT (example):
          {
            "results": [
              {
                "url": "...",
                "success": true,
                "content": "cleaned page text or markdown",
                "error": null
              },
              ...
            ]
          }
        """
        
        try:
            urls = []
            
            # Collect URLs from both parameters
            if "urls" in args and args["urls"]:
                urls.extend(args["urls"])
            
            if "url" in args and args["url"]:
                urls.append(args["url"])
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            if not unique_urls:
                return {"error": "No valid URLs provided"}
            
            # If only one URL, use the single URL method for backward compatibility
            if len(unique_urls) == 1:
                url = unique_urls[0]
                page_data = self.serp_helper.get_webpage(url)
                return {
                    "results": [{
                        "url": url,
                        "success": bool(page_data),
                        "content": page_data,
                        "error": None if page_data else "Failed to scrape content"
                    }]
                }
            
            # Process multiple URLs in parallel
            results = self.serp_helper.get_webpages_parallel(unique_urls)
            return {"results": results}
        
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}
        

    def _tool_generate_pdf(self, args: dict) -> dict:
        """
        INPUT: {"title": "...", "content": "...", "page_size": "A4 portrait"}
        OUTPUT: {"data": "<pdf_url>", "success": True/False, "error": "..."}
        """
        try:
            content = args.get("content", "")
            title = args.get("title", "Document")
            page_size = args.get("page_size", "A4 portrait")
            if not content.strip():
                return {"success": False, "error": "Content is empty"}
            result = self.pdf_generator_helper.generate_pdf(content=content, title=title, page_size=page_size)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def format_messages(self, data: Dict[str, Any],persona = None) -> List[Dict[str, Any]]:
        """
        Convert Mongo-style conversation document into a list of message dicts.
        """
        
        current_ts = int(datetime.now(timezone.utc).timestamp())
        
        system_message=None
        if(not system_message):
                system_message = """"""
        
        formatted: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": f"""{system_message}

You are an expert AI assistant specialized in HR laws, compliance, and court decisions. Your goal is to provide comprehensive, well-researched, and authoritative responses.

# Context
- Current Unix timestamp: {current_ts}
- Interpret all relative dates (e.g., "today", "this year", "after July 2024") against this timestamp.

# Knowledge & Tools
You have access to:
- Curated HR/legal knowledge in a vector DB (Pinecone) with metadata fields:
  location_slug, primary_industry_slug, secondary_industry_slug, region_slug, topic_slug, discussedTimestamp
- Slug vector stores for resolving fuzzy user text into canonical slugs
- A SERP tool for fresh, real-time web results
- A web content fetcher to extract clean text from URLs (can process multiple URLs in parallel)
- A PDF Generator: generate_pdf to create downloadable PDF documents

# Research Methodology - BE THOROUGH
1) **Resolve Filters First**: If query contains location/topic/industry/region → call resolve_filter_slug with ALL required queries at once.

2) **Multi-Source Research**: 
   - ALWAYS query curated store → search_documents (use top_k=15-20 for comprehensive results)
   - MANDATORY: Before using filters, get correct values from resolve_filter_slug - never guess filter values
   - When user implies time: use discussedTimestamp_gt/lt filters
   - For current/latest information: ALSO use fetch_serp_content to get real-time web results
   - Extract content from relevant URLs using get_webpage_content (process multiple URLs in parallel)

3) **Cross-Reference Sources**: 
   - Combine information from vector DB, web search, and scraped content
   - Look for patterns, contradictions, and consensus across sources
   - Verify dates and recency of information

4) **PDF Generation**: When user requests a PDF:
   - IMMEDIATELY call generate_pdf tool
   - Include all relevant researched content
   - Use descriptive title based on the query
   - Trigger phrases: "create a PDF", "generate PDF", "download", "export as PDF", "save as document"

# Response Format - ALWAYS STRUCTURE YOUR RESPONSE THIS WAY:

## SUMMARY
Provide a concise 2-4 sentence overview that directly answers the user's question. Include key takeaways and main findings.

## DETAILS
REMEMBER: Users want in-depth, research-backed answers, not superficial summaries. Be thorough, authoritative, and comprehensive.
                """
            }
        ]

        for msg in data.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content")

            if role == "user":
                formatted.append({
                    "role": role,
                    "content": content
                })
            elif role == "assistant":
                if content:  # assistant with content
                    formatted.append({
                        "role": role,
                        "content": content
                    })
                else:  # assistant with no content -> tool_calls
                    formatted.append(msg)
            elif role == "tool":
                formatted.append(msg)  # keep as is

        return formatted

    def remove_duplicates(self, tool_call_responses):
        seen = set()
        unique = []
        for r in tool_call_responses:
            key = json.dumps(r, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique