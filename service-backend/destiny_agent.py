import os
import json
import yaml
import time
import random
import re
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

import logging as log
from config import config
from sqlite_adapter import SQLConnect
# Pydantic models for structured output

class FilterResponse(BaseModel):
    """Expected response format from the filter agent"""
    Matched: Dict[str, List[str]] = Field(description="UIDs of matched users with reasons")
    Filtered: Dict[str, List[str]] = Field(description="UIDs of filtered users with reasons")


class FilterAgent:
    def __init__(self, openai_api_key, log):
        # Setup your LLM (choose gpt-4o / gpt-3.5-turbo etc.)
        self.log = log
        try:
            self.llm = ChatOpenAI(
                model=config.OPENAI_MODEL_NAME, 
                temperature=0.7,
                openai_api_key=openai_api_key,
                model_kwargs={"response_format": {"type": "json_object"}}
            )
            log.info(f"LLM initialized with JSON mode: {config.OPENAI_MODEL_NAME}")
        except Exception as e:
            log.warning(f"Failed to initialize LLM with JSON mode: {e}")
            # Fallback without JSON mode
            self.llm = ChatOpenAI(
                model=config.OPENAI_MODEL_NAME, 
                temperature=0.7,
                openai_api_key=openai_api_key
            )
            log.info(f"LLM initialized without JSON mode: {config.OPENAI_MODEL_NAME}")

    def __call__(self, user_details, enhanced_cards):
        """
        Use LLM to filter and match cards with structured JSON output.
        Returns a dictionary with 'Matched' and 'Filtered' keys.
        """
        with open(config.PROMPTS_YAML, "r") as file:
            prompts = yaml.safe_load(file)
            
        filter_user_prompt = prompts['filter_user_prompt'].format(
            user_details=user_details, 
            recommended_cards=enhanced_cards
        )
        
        self.log.info(f"Sending prompt to LLM (first 200 chars): {filter_user_prompt[:200]}...")

        try:
            # Create message with clear JSON instruction
            messages = [SystemMessage(content=prompts['filter_system_prompt'])]

            messages.append(HumanMessage(content=filter_user_prompt))
            
            # Get response from LLM (configured for JSON output)
            response = self.llm(messages)
            response_content = response.content.strip()
            
            self.log.info(f"LLM response received, length: {len(response_content)} chars")
            
            # Clean up the response content (remove markdown if present)
            if response_content.startswith('```json'):
                response_content = response_content.replace('```json', '').replace('```', '').strip()
            elif response_content.startswith('```'):
                response_content = response_content.replace('```', '').strip()
            
            self.log.info(f"Raw response content: {response_content[:200]}...")
            
            # Try to parse JSON response
            try:
                response_json = json.loads(response_content)
                self.log.info(f"Successfully parsed JSON")
            except json.JSONDecodeError as json_err:
                self.log.error(f"JSON parsing failed: {json_err}")
                self.log.error(f"Full response content: {response_content}")
                raise
            
            # Validate the structure matches our expected format
            if not isinstance(response_json, dict):
                raise ValueError(f"Response is not a dictionary: {type(response_json)}")
            
            if "Matched" not in response_json and "Filtered" not in response_json:
                raise ValueError(f"Response missing required keys 'Matched' or 'Filtered'. Got keys: {list(response_json.keys())}")
            
            if len(response_json["Matched"]) == 0:
                raise ValueError(f"All cards rejected. Got keys: {list(response_json.keys())}")
            
            # Ensure all values are in the correct format
            for section_name in ["Matched", "Filtered"]:
                section = response_json[section_name]
                if not isinstance(section, dict):
                    raise ValueError(f"'{section_name}' must be a dictionary, got {type(section)}")
                
                for uid, reasons in section.items():
                    if not isinstance(reasons, list):
                        # Convert single reason to list
                        response_json[section_name][uid] = [str(reasons)]
                    elif len(reasons) == 0:
                        # Add default reasons if empty
                        response_json[section_name][uid] = ["No specific reason provided", "General compatibility"]
            
            self.log.info(f"Successfully parsed and validated JSON response")
            return response_json
            
        except json.JSONDecodeError as e:
            self.log.error(f"JSON parsing failed: {e}")
            self.log.error(f"Response content: {response_content}")
            return self._create_fallback_response(enhanced_cards)
            
        except Exception as e:
            self.log.error(f"Filter agent error: {e}")
            return self._create_fallback_response(enhanced_cards)

    def _create_fallback_response(self, enhanced_cards):
        """Create a fallback response when LLM filtering fails"""
        fallback_response = {
            "Matched": {},
            "Filtered": {}
        }
        
        # Add all cards to matched with default reasons
        for card in enhanced_cards:
            fallback_response["Matched"][card['UID']] = [
                "Not Present", 
                "Not Present"
            ]
        
        self.log.warning("Using fallback response - all cards marked as matched")
        return fallback_response


class SimpleChatSystem:
    """
    Simplified chat system that handles both app-initiated and user-initiated chats
    """
    
    def __init__(self):
        self.llm = None  # Will be initialized when first needed
        
        # Load prompts
        self.prompts = self._load_prompts()
        


    def _get_openai_key(self):
        """Get OpenAI API key from secrets"""
        # Import locally to avoid circular import
        from backend import get_secrets
        secrets = get_secrets(config.aws_secrets_group)
        return secrets['OPENAI_API_KEY']

    def _initialize_llm(self):
        """Initialize the LLM client if not already done"""
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=config.OPENAI_MODEL_NAME, 
                temperature=0.7,
                openai_api_key=self._get_openai_key()
            )

    def _load_prompts(self):
        """Load prompts from YAML file"""
        with open(config.PROMPTS_YAML, 'r') as file:
            return yaml.safe_load(file)



    def _apply_filter(self, uid: str, query: str) -> Dict[str, Any]:
        """Apply filter using the existing backend filter function"""
        try:
            # Import locally to avoid circular import
            from backend import live_filter
            return live_filter(uid, query)
        except Exception as e:
            log.error(f"Error applying filter: {str(e)}")
            return {
                'RESPONSE': f"Error applying filter: {str(e)}",
                'RECOMMENDATIONS': []
            }

    def _generate_response(self, system_prompt: str, user_input: str, history: List[Dict] = None) -> str:
        """Generate response using OpenAI directly"""
        try:
            self._initialize_llm()  # Initialize LLM if not already done
            
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history
            if history:
                for msg in history:
                    if msg.get('role') == 'user':
                        messages.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        messages.append(SystemMessage(content=f"Assistant: {msg.get('content', '')}"))
            
            # Add current user input
            messages.append(HumanMessage(content=user_input))
            
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"I apologize, but I'm having trouble processing your request right now. Please try again."

    def _generate_response_with_tools(self, system_prompt: str, user_input: str, history: List[Dict] = None) -> Dict[str, Any]:
        """Generate response with tool calling capability"""
        try:
            self._initialize_llm()  # Initialize LLM if not already done
            
            # Enhanced system prompt with tool instructions
            enhanced_system_prompt = f"""{system_prompt}

You have access to a filter tool. When the user asks to filter, show only specific people, or wants to see matches based on certain criteria (like location, age, profession, etc.), respond with:

TOOL_CHOICE: filter
FILTER_STATEMENT: [provide a clear, one-line filter statement based on user's request]

Otherwise, respond normally with conversational text.

Examples:
- User: "Show me only people from Mumbai" → TOOL_CHOICE: filter, FILTER_STATEMENT: people from Mumbai
- User: "I want to see matches aged 25-30" → TOOL_CHOICE: filter, FILTER_STATEMENT: people aged 25-30
- User: "Filter by engineers only" → TOOL_CHOICE: filter, FILTER_STATEMENT: engineers only
- User: "How are you doing?" → [normal conversational response]"""

            messages = [SystemMessage(content=enhanced_system_prompt)]
            
            # Add conversation history
            if history:
                for msg in history:
                    if msg.get('role') == 'user':
                        messages.append(HumanMessage(content=msg.get('content', '')))
                    elif msg.get('role') == 'assistant':
                        messages.append(SystemMessage(content=f"Assistant: {msg.get('content', '')}"))
            
            # Add current user input
            messages.append(HumanMessage(content=user_input))
            
            response = self.llm.invoke(messages)
            response_content = response.content
            
            # Parse response for tool usage
            if "TOOL_CHOICE: filter" in response_content:
                # Extract filter statement
                filter_match = re.search(r'FILTER_STATEMENT:\s*(.+)', response_content)
                if filter_match:
                    filter_statement = filter_match.group(1).strip()
                    return {
                        'tool_choice': 'filter',
                        'filter_statement': filter_statement,
                        'response': response_content
                    }
            
            return {
                'tool_choice': 'chat',
                'response': response_content
            }
            
        except Exception as e:
            return {
                'tool_choice': 'chat',
                'response': f"I apologize, but I'm having trouble processing your request right now. Please try again."
            }

    def initiate_chat(self, chat_type: str, uid: str, user_input: str = None, history: List[Dict] = None, log = log):
        """
        Main entry point for both chat types
        """
        self.log = log
        if chat_type == "app_initiated":
            return self.handle_hobby_chat(uid, user_input, history or [])
        elif chat_type == "user_initiated":  
            return self.handle_preference_chat(uid, user_input, history or [])
        elif chat_type == "match_initiate":
            return self.handle_match_chat(uid, user_input, history or [])
        else:
            raise ValueError(f"Invalid chat_type: {chat_type}")

    def handle_hobby_chat(self, uid: str, user_input: str = None, history: List[Dict] = None):
        """Handle app-initiated hobby conversations"""
        
        # Get user details
        user_details = self._get_user_details(uid)
        if not user_details:
            return {"error": "User not found"}

        name = user_details['NAME']
        hobbies = user_details['HOBBIES']
        
        # Load previous chats
        previous_chats = self._load_previous_chats(user_details.get('INITIATE_CHATS'))
        
        # Create system prompt
        system_prompt = self.prompts['initiate_system_prompt'].format(
            name=name, 
            hobbies=hobbies, 
            previous_chats=previous_chats
        )

        if user_input is None:
            # Starting new conversation
            opening_message = self._generate_response(
                system_prompt,
                f"Start a friendly conversation with {name} about their hobbies."
            )
            
            history = [
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": opening_message}
            ]
            
            return {
                "message": opening_message,
                "history": history,
                "continue": True,
                "chat_type": "app_initiated"
            }
        else:
            # Continue conversation
            return self._continue_hobby_chat(uid, user_input, history, system_prompt)

    def _continue_hobby_chat(self, uid: str, user_input: str, history: List[Dict], system_prompt: str):
        """Continue hobby conversation"""
        
        # Check for exit phrases
        if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye', 'end']:
            goodbye_phrases = [
                'Thank you for chatting with me! This information helps us find better matches for you.',
                'See you later! We will further discuss your hobbies some other time.'
            ]
            goodbye = random.choice(goodbye_phrases)
            
            # Save chat history
            self._save_chat_history(uid, history, 'INITIATE_CHATS')
            
            return {
                "message": goodbye,
                "history": history + [{"role": "user", "content": user_input}, {"role": "assistant", "content": goodbye}],
                "continue": False
            }

        # Check conversation length
        if len(history) > config.MAX_DESTINY_CHAT * 2:
            end_msg = 'I have been instructed to keep conversations short. Thank you for chatting with me! This information helps us find better matches for you.'
            self._save_chat_history(uid, history, 'INITIATE_CHATS')
            
            return {
                "message": end_msg,
                "history": history + [{"role": "user", "content": user_input}, {"role": "assistant", "content": end_msg}],
                "continue": False
            }

        # Generate response
        assistant_msg = self._generate_response(system_prompt, user_input, history)
        
        updated_history = history + [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": assistant_msg}
        ]

        # Check if conversation should end
        continue_chat = "thank you for chatting" not in assistant_msg.lower()
        if not continue_chat:
            self._save_chat_history(uid, updated_history, 'INITIATE_CHATS')

        return {
            "message": assistant_msg,
            "history": updated_history,
            "continue": continue_chat
        }

    def handle_preference_chat(self, uid: str, user_input: str, history: List[Dict]):
        """Handle user-initiated preference conversations"""
        
        # Check for exit phrases
        if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye', 'end']:
            goodbye_phrases = [
                'Thank you for chatting with me! This information helps us find better matches for you.',
                'See you later! We will further discuss your preferences some other time.'
            ]
            goodbye = random.choice(goodbye_phrases)
            
            self._save_chat_history(uid, history, 'PREFERENCE_CHATS')
            
            return {
                "message": goodbye,
                "history": history + [{"role": "user", "content": user_input}, {"role": "assistant", "content": goodbye}],
                "continue": False
            }

        # Get user details
        user_details = self._get_user_details(uid)
        if not user_details:
            return {"error": f"User not found with uid: {uid}"}

        name = user_details['NAME']
        
        # Check if this is a new conversation
        if not history or not any(msg.get("role") == "system" for msg in history):
            # Load previous chats
            previous_chats = self._load_previous_chats(user_details.get('PREFERENCE_CHATS'))
            
            # Create system prompt
            system_prompt = self.prompts['preference_system_prompt'].format(
                name=name, 
                previous_chats=previous_chats
            )
            
            history = [{"role": "system", "content": system_prompt}]

        # Generate response with tool calling capability
        system_prompt = history[0]['content'] if history else ""
        llm_response = self._generate_response_with_tools(system_prompt, user_input, history)
        
        # Check if LLM chose to use filter tool
        if llm_response.get('tool_choice') == 'filter':
            # Apply filter using the LLM-generated filter statement
            filter_statement = llm_response.get('filter_statement', user_input)
            filter_result = self._apply_filter(uid, filter_statement)

            # Its adding two exit messages so commenting it out
            
            # # Generate filter confirmation message
            # filter_responses = [
            #     "I've applied the filter to your recommendations.",
            #     "Your recommendations have been filtered as requested.",
            #     "I've updated your matches based on your preferences.",
            #     "Filter applied successfully to your recommendations."
            # ]
            
            # base_message = random.choice(filter_responses)

            response_message = f"{filter_result['RESPONSE']}"
            
            updated_history = history + [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response_message}
            ]
            
            return {
                "message": response_message,
                "history": updated_history,
                "continue": True,
                "filter_applied": True,
                "recommendations": filter_result.get('RECOMMENDATIONS', [])
            }
        else:
            # Regular chat response
            assistant_msg = llm_response.get('response', '')
            
            updated_history = history + [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_msg}
            ]

            return {
                "message": assistant_msg,
                "history": updated_history,
                "continue": True
            }

    def _get_user_details(self, uid: str) -> Optional[Dict]:
        """Get user details from database"""
        try:
            profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
            select_sql = f"SELECT UID, NAME, DOB, CITY, COUNTRY, HOBBIES, PROFESSION, GENDER, INITIATE_CHATS, PREFERENCE_CHATS, QUESTION1, QUESTION2, QUESTION3 FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
            profile_connect.cursor.execute(select_sql)
            result = profile_connect.cursor.fetchone()

            profile_connect.close()
            #self.log.info(f'Result: {result}')
            
            return result
        except Exception as e:
            self.log.error(f"Error getting user details: {e}")
            return None

    def _load_previous_chats(self, chats_url: str) -> str:
        """Load previous chat history from S3"""
        try:
            # Import locally to avoid circular import
            from backend import load_previous_chats
            return load_previous_chats(chats_url)
        except Exception as e:
            self.log.error(f"Error loading previous chats: {e}")
            return ""

    def _save_chat_history(self, uid: str, history: List[Dict], column: str):
        """Save chat history to S3"""
        try:
            import threading
            # Import locally to avoid circular import
            from backend import update_notifications_or_chats, run_async_task
            
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            threading.Thread(
                target=run_async_task, 
                args=(update_notifications_or_chats(uid, [{'history': history, 'updated': current_time}], column),)
            ).start()
        except Exception as e:
            self.log.error(f"Error saving chat history: {e}")


# Initialize the simple chat system for direct use
chat_flow = SimpleChatSystem() 