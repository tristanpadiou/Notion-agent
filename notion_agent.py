from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent,RunContext
from pydantic_ai.messages import ModelMessage
from dataclasses import dataclass
from composio_langgraph import Action, ComposioToolSet, App




@dataclass
class Deps:
    messages:list[ModelMessage]
    agent_notes:str

class Notionagent:
    def __init__(self, mcp_server_url:str, api_keys:dict):
        self.mcp_server_url=mcp_server_url
        self.api_keys=api_keys
        self.tools=ComposioToolSet(api_key=api_keys['composio_key'])
        self.tool_shemas={
            'Notion Manager':{tool.name:tool for tool in self.tools.get_action_schemas(apps=[App.NOTION])}}
        self.deps=Deps(messages=[],agent_notes="")
        self.llm=OpenAIModel('gpt-4.1-nano',provider=OpenAIProvider(api_key=api_keys['openai_api_key']))
        self.mcp_server=MCPServerStreamableHTTP(self.mcp_server_url)

        async def agent_notes(ctx:RunContext[Deps],query:str):
            """Use this tool to write notes to improve the agent's performance based on feedback
            args:
            - query:str
            """
            note_agent=Agent(self.llm,instructions="write notes or modify the previous notes to improve the agent's performance based on feedback")
            note_result=note_agent.run_sync(f"previous notes: {ctx.deps.agent_notes if ctx.deps.agent_notes else 'no previous notes'}\n\n feedback: {query}")
            ctx.deps.agent_notes=note_result.output
            return "Agent notes updated"
        
        self.agent=Agent(self.llm, mcp_servers=[self.mcp_server],tools=[agent_notes], instructions="you are a helpful assistant that can help with tasks related to Notion\
                         you have access to a set of tools to help you with your tasks and a notes tool to improve your performance,\
                         you can use the notes to improve your performance and to help you with your tasks")
    async def chat(self,query:str):
        async with self.agent.run_mcp_servers():  
            result = await self.agent.run(f"user query: {query}\n\n previous notes: {self.deps.agent_notes if self.deps.agent_notes else 'no previous notes'}",deps=self.deps, message_history=self.deps.messages)
            self.deps.messages=result.all_messages()
        return result.output

    def reset(self):
        self.deps.messages=[]
        self.deps.agent_notes=""