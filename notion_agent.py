from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from dataclasses import dataclass
from composio_langgraph import Action, ComposioToolSet, App
from dotenv import load_dotenv
load_dotenv()
import os
import logfire
logfire_token = os.getenv('logfire_token')
if logfire_token:
    logfire.configure(token=logfire_token)
    logfire.instrument_pydantic_ai()

@dataclass
class Message_state:
    messages:list[ModelMessage]

class Notionagent:
    def __init__(self, mcp_server_url:str, api_keys:dict):
        self.mcp_server_url=mcp_server_url
        self.api_keys=api_keys
        self.tools=ComposioToolSet(api_key=api_keys['composio_key'])
        self.tool_shemas={
            'Notion Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.NOTION])}}
        self.memory=Message_state(messages=[])
        self.llm=OpenAIModel('gpt-4.1-nano',provider=OpenAIProvider(api_key=api_keys['openai_api_key']))
        self.mcp_server=MCPServerStreamableHTTP(self.mcp_server_url)
        self.agent=Agent(self.llm, mcp_servers=[self.mcp_server])

    async def chat(self,query:str):
        async with self.agent.run_mcp_servers():  
            result = self.agent.run_sync(query, message_history=self.memory.messages)
            self.memory.messages=result.all_messages()
        return result.output

    def reset(self):
        self.memory.messages=[]