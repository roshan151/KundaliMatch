from langchain.chat_models import ChatOpenAI
from crewai import Agent as CrewAgent
from crewai import Task, Crew

from crewai import Agent, Task, Crew
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Union

class ConversationResponse(BaseModel):
    messages: List[Union[str, dict]] = Field(
        ...,
        description="Alternating assistant and user messages"
    )




class Agent:

    def __init__(self, user_data, model  = 'gpt-4'):
        llm = ChatOpenAI(model=model, temperature=0.7)

        # Create a conversational agent
        conversation_agent = CrewAgent(
            role="Conversational Match Assistant",
            goal="Understand user preferences based on hobbies",
            backstory=(
                "You are an AI assistant designed to understand user's interests by having a casual conversation. "
                "Focus on their hobbies and extract detailed preferences in a friendly tone."
            ),
            llm = llm,
            verbose=True,
        )

        parser = PydanticOutputParser(pydantic_object=ConversationResponse)
        conversation_task = Task( description=(
                                    f"""
                                    Start a conversation with the user {user_data['name']} who enjoys {', '.join(user_data['hobbies'])}.
                                    Ask friendly questions about their hobbies and follow up based on what they say.

                                    End with "Thank you for chatting, this information helps us find better matches for you."

                                    Please format the full conversation as a JSON object like this:
                                    {{
                                        "messages": [
                                            {{"assistant": "Hi! You said you enjoy movies..."}},
                                            {{"user": "Yes, I love Pulp Fiction."}},
                                            {{"assistant": "Are you a Tarantino fan?"}},
                                            ...
                                            {{"assistant": "Thank you for chatting..."}}
                                        ]
                                    }}
                                    """
                                ),
                                expected_output="A JSON object with key 'messages' containing alternating assistant/user turns",
                                agent=conversation_agent,
                                output_parser=parser )

        # Create the crew and run it
        self.crew = Crew(
            agents=[conversation_agent],
            tasks=[conversation_task],
            verbose=True
        )

    def start(self):
        print(self.crew.kickoff())