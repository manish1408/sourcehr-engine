import json
import os
from datetime import datetime
from typing import Dict, List

from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from app.schemas.Dashboard import NewsList


class NewsWriterAgent:
    """Transforms researched snippets into structured news items."""

    def __init__(self) -> None:
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("gpt-4o-mini"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )

    def compose_news(
        self,
        dashboard_context: Dict[str, List[str]],
        research_payload: Dict[str, List[Dict]],
        max_items: int = 5,
    ) -> NewsList:
        system_message = SystemMessage(
            content="""You are a senior HR legal analyst. Blend curated knowledge with fresh web findings to craft concise, high-impact news briefs for employers."""
        )

        payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "dashboard": dashboard_context,
            "research": research_payload,
            "max_items": max_items,
        }

        user_message = HumanMessage(
            content="""Using the provided dashboard filters and research context, produce up to {max_items} unique employment-law news items relevant to the organization's footprint. Each item must include:
- title (<= 110 characters)
- description (2-3 sentences, clear on employer impact)
- sourceUrl (source link if available)
Ensure coverage spans different jurisdictions or topics when possible.

Research payload:
{payload}
""".format(max_items=max_items, payload=json.dumps(payload, ensure_ascii=False, indent=2))
        )

        structured_llm = self.chat.with_structured_output(NewsList)
        response = structured_llm.invoke([system_message, user_message])
        return response


