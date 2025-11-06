from typing import Any
from langchain_openai import AzureChatOpenAI
from langsmith import Client
from dotenv import load_dotenv
import os

from fastapi import UploadFile
import tempfile
from openai import AzureOpenAI
from openevals.llm import create_llm_as_judge
from openevals.prompts import RAG_GROUNDEDNESS_PROMPT,HALLUCINATION_PROMPT,CONCISENESS_PROMPT,CORRECTNESS_PROMPT,RAG_RETRIEVAL_RELEVANCE_PROMPT
from app.helpers.AIChat import AIChat
from app.models.Evaluation import EvaluationModel
from app.models.EvaluationDataset import EvaluationDatasetModel
from app.schemas.Evaluation import EvaluationScores

load_dotenv()

class EvaluationService:
    def __init__(self):
        self.evaluation_model = EvaluationModel()
        self.client = Client()
        self.evaluation_dataset_model=EvaluationDatasetModel()
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )
         

        

    def upload_csv_dataset(
        self,
        file: UploadFile,
        name: str,
        description: str,
        input_keys: list,
        output_keys: list
    ):
        try:
            
            # Save the uploaded file to a temporary location
            suffix = os.path.splitext(file.filename)[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file.file.read())
                tmp_path = tmp.name

            # Upload the CSV to LangSmith
            dataset = self.client.upload_csv(
                csv_file=tmp_path,
                input_keys=input_keys,
                output_keys=output_keys,
                name=name,
                description=description,
                data_type="kv"
            )

            os.remove(tmp_path)
            self.evaluation_dataset_model.create_evaluation_dataset({
                "datasetId":dataset.id,
                "datasetName":name,
                "description":description
            }
                
            )
            data= {
                "datasetId": dataset.id,
                "name": dataset.name,
                "status": "uploaded"
            }
            return {
                            "success": True,
                            "data": data
                        }
        except Exception as e:
                return{    
                    "success": False,
                    "data": None,
                    "error":str(e)
                }

    async def call_llm_from_app(self, question: str) -> tuple[str, str, Any]:
        ai_chat = AIChat("source-hr-knowledge")
        session = {
            "sessionId": "evaluation-session",
            "messages": []
        }

        content = ""
        tool_output = ""
        citations = None

        try:
            async for chunk in ai_chat.chat_with_knowledge_stream_openai_tools(question, session):
                if chunk:
                    if "content" in chunk:
                        content += chunk["content"]
                    if "citations" in chunk and "tool_output" in chunk:
                        tool_output = chunk["tool_output"]
                        citations = chunk["citations"]
        except Exception as e:
            print(f"[Error while streaming LLM response]: {str(e)}")

        return content.strip(), tool_output.strip(), citations


            
    async def evaluate_langsmith_dataset(self,dataset_id: str):
        try:
            print("Evaluation started")
            examples = list(self.client.list_examples(dataset_id=dataset_id))

            if not examples:
                return {"success": False, "message": "No examples found"}

            rag_groundedness_evaluator = create_llm_as_judge(
                prompt=RAG_GROUNDEDNESS_PROMPT,
                judge=self.llm,
                model="gpt-4o-mini",
                feedback_key="groundedness",
                continuous=True
            )
            hallucination_evaluator = create_llm_as_judge(
                prompt=HALLUCINATION_PROMPT,
                judge=self.llm,
                model="gpt-4o-mini",
                feedback_key="groundedness",
                continuous=True
            )
            rag_retrieval_relevance_evaluator= create_llm_as_judge(
                prompt=RAG_RETRIEVAL_RELEVANCE_PROMPT,
                judge=self.llm,
                model="gpt-4o-mini",
                feedback_key="groundedness",
                continuous=True
            )
            correctness_evaluator= create_llm_as_judge(
                prompt=CORRECTNESS_PROMPT,
                judge=self.llm,
                model="gpt-4o-mini",
                feedback_key="groundedness",
                continuous=True
            )
            conciseness_evaluator= create_llm_as_judge(
                prompt=CONCISENESS_PROMPT,
                judge=self.llm,
                model="gpt-4o-mini",
                feedback_key="groundedness",
                continuous=True
            )

            for example in examples:
                input_data = example.inputs
                user_query = input_data.get("question") or list(input_data.values())[0]
                reference = example.outputs.get("Output")

                prediction, tool_output,citations = await self.call_llm_from_app(user_query)

                rag_groundedness_result = rag_groundedness_evaluator(
                    outputs=prediction,
                    context=tool_output
                )
                hallucination_result=hallucination_evaluator(
                    inputs=user_query,
                    outputs=prediction,
                    context=tool_output,
                    reference_outputs=reference
                )
                
                rag_retrieval_relevance_result=rag_retrieval_relevance_evaluator(
                    inputs=user_query,
                    context=tool_output    
                    )
                correctness_result=correctness_evaluator(
                    inputs=user_query,
                    outputs=prediction,
                    reference_outputs=reference
                )
                conciseness_result=conciseness_evaluator(
                    inputs=user_query,
                    outputs=prediction
                )
                scores = EvaluationScores(
                    rag_groundedness=rag_groundedness_result["score"],
                    hallucination=hallucination_result["score"],
                    rag_retrieval_relevance=rag_retrieval_relevance_result["score"],
                    correctness=correctness_result["score"],
                    conciseness=conciseness_result["score"]
                )
                self.evaluation_model.create_evaluation({
                    "userQuery": user_query,
                    "output":prediction,
                    "scores": scores.model_dump(),
                    "citations": citations,
                    "referenceOutput": reference,
                    "datasetId":dataset_id
                })
            print("Evaluation Completed")

        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    def delete_evaluation_dataset(self, dataset_id: str) -> dict:
        try:
            deleted = self.evaluation_dataset_model.delete_evaluation_dataset(dataset_id)
            return {
                "success": True,
                "data": "Dataset  deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete dataset: {str(e)}"
            }
            
    def get_evaluation(self,evaluation_id):
        try:
            data=self.evaluation_model.get_evaluation_by_id(evaluation_id)
            return{
                        "success": True,
                        "data": data
                    }
        except Exception as e:
            return{    
                "success": False,
                "data": None,
                "error":str(e)
            }
            
            
    def get_all_evaluations(self,page,limit=10):
        total_docs = self.evaluation_model.get_documents_count({})
        limit = limit
        total_pages = (total_docs + limit - 1) // limit
        number_to_skip = (page - 1) * limit
        docs = self.evaluation_model.get_all_evaluations({}, number_to_skip, limit)
        
        if not docs:
                return {
                    "success": False,
                    "data": None,
                    "error": "No documents found"
                }

        return {
                "success": True,
                "data": {
                    "docs": docs,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
            
            