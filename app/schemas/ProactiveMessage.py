from typing import List

from pydantic import BaseModel

    
class ProactiveMessages(BaseModel):
    proactiveMessages: List[str]
