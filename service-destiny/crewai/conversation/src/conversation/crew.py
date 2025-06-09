# src/latest_ai_development/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from langchain.chat_models import ChatOpenAI
# src/latest_ai_development/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from crewai_tools import SerperDevTool
import logging as log

from dotenv import load_dotenv
load_dotenv()
log.basicConfig(
    format='%(levelname)s [%(filename)s:%(lineno)d] %(message)s',
    level=log.INFO
    )

@CrewBase
class Conversation():
  """Conversation crew"""

  agents: List[BaseAgent]
  tasks: List[Task]
  llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.7)
  
  @agent
  def conversational(self) -> Agent:
    return Agent(
      config=self.agents_config['conversational'], # type: ignore[index]
      verbose=True,
      tools=[SerperDevTool()],
      llm = self.llm
    )

  @task
  def conversation_task(self) -> Task:
    return Task(
      config=self.tasks_config['conversation_task'], # type: ignore[index]
    )

  @crew
  def crew(self) -> Crew:
    """Creates the LatestAiDevelopment crew"""
    return Crew(
      agents=self.agents, # Automatically created by the @agent decorator
      tasks=self.tasks, # Automatically created by the @task decorator
      process=Process.sequential,
      verbose=True,
    )
  
  @before_kickoff
  def before_kickoff_function(self, inputs):
    print(f"Before kickoff function with inputs: {inputs}")
    return inputs # You can return the inputs or modify them as needed

  @after_kickoff
  def after_kickoff_function(self, result):
    print(f"After kickoff function with result: {result}")
    return result # You can return the result or modify it as needed
  