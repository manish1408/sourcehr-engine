from datetime import datetime
import os
import json
from dotenv import load_dotenv


from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from openai import AsyncAzureOpenAI
from langsmith import traceable,tracing_context,wrappers

from app.schemas.ChatSession import ChatSessionTitle
from app.helpers.VectorDB import VectorDB
from app.schemas.ProactiveMessage import ProactiveMessages

load_dotenv()

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
        self.vector_retriever = self.vector_database.get_vector_retriever()
        self.latest_citations = []

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

    async def chat_with_knowledge_stream_openai_tools(self, question, session):
        try:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_knowledge_base",
                        "description": "Searches the knowledge base for relevant information to answer the user's question.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The user's question to search for."
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ]

            chat_history = []
            for message in session.get("messages", []):
                if message["messageType"] == "user":
                    chat_history.append({"role": "user", "content": message["message"]})
                elif message["messageType"] == "assistant":
                    chat_history.append({"role": "assistant", "content": message["message"]})
            chat_history.append({"role": "user", "content": question})

            response = await self._openai_tool_call(
                chat_history,
                tools,
                metadata={
                    "question": question,
                    "session_id": session.get("sessionId"),
                    "tool_used": True
                }
            )

            message = response.choices[0].message
            citations = []
            tool_output = ""

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "search_knowledge_base":
                        tool_args = json.loads(tool_call.function.arguments)
                        query = tool_args["query"]
                        docs = self.vector_retriever.invoke(query)

                        docs_as_string = ''
                        citations_list = []
                        seen_citations = set()
                        for doc in docs:
                            docs_as_string += f"{doc.page_content} \n Created On: {doc.metadata.get('ingestion_date')} \n\n"

                            file_url = doc.metadata.get('file_url')
                            file_name = doc.metadata.get('file_name')
                            page_url = doc.metadata.get('pageUrl')
                            source_default = doc.metadata.get('source')

                            citation_obj = {}
                            if file_url:
                                citation_obj["file_url"] = file_url
                            if file_name:
                                citation_obj["file_name"] = file_name
                            if page_url:
                                citation_obj["pageUrl"] = page_url
                            if source_default:
                                citation_obj["source"] = source_default

                            if citation_obj:
                                key = (
                                    citation_obj.get("file_url"),
                                    citation_obj.get("file_name"),
                                    citation_obj.get("pageUrl"),
                                    citation_obj.get("source"),
                                )
                                if key not in seen_citations:
                                    seen_citations.add(key)
                                    citations_list.append(citation_obj)

                        citations = citations_list
                        tool_output = docs_as_string

                        chat_history.append({
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [tool_call.to_dict() if hasattr(tool_call, 'to_dict') else vars(tool_call)]
                        })
                        chat_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "search_knowledge_base",
                            "content": tool_output
                        })

                        stream = await self._openai_stream_response(
                            chat_history,
                            metadata={
                                "question": question,
                                "citations": citations,
                                "reference_context": tool_output,
                                "session_id": session.get("sessionId")
                            }
                        )

                        async for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield {
                                    "content": chunk.choices[0].delta.content,
                                    "citations": citations,
                                    "tool_output":tool_output

                                }
                        return

            # If no tool was used
            stream = await self._openai_stream_response(
                chat_history + [message],
                metadata={
                    "question": question,
                    "citations": [],
                    "reference_context": "",
                    "session_id": session.get("sessionId"),
                    "tool_used": False
                }
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "content": chunk.choices[0].delta.content,
                        "citations": [],
                        "tool_output":tool_output
                    }

        except Exception as e:
            print(str(e))
            yield None

    def get_chat_session_title(self, question: str, answer: str) -> ChatSessionTitle:
        structured_llm = self.chat.with_structured_output(ChatSessionTitle)
        final_resp = structured_llm.invoke(
            f"Extract meaningful chat session title from this conversation:\nQuestion: {question}\nAnswer: {answer}"
        )
        return final_resp
    
        
    def generateProactiveMessages(self,conversationHistory,dashboard_info):
          
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
            - **Naturally embed** the jurisdiction (location), topic, and industry — do NOT list them like keywords.
            - Vary the **intent**: ask a question, request information.
            - **Vary sentence structure** across the 5 messages. Do not repeat patterns like "Can we..."/"Check if..."
            - Use a professional but conversational tone.
            - Avoid robotic or templated phrasing.
            - Do not mention that the user dropped off.
            """
        )


        messages = [
            system_message,
            HumanMessage(content=f"Generate the 5 follow-up messages for this conversation history: {conversationHistory}")
        ]
        structured_llm = self.chat.with_structured_output(ProactiveMessages)

        response=structured_llm.invoke(messages)
        return response
    
    def extract_messages_from_last_system(self,conversation_):
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
    
    
