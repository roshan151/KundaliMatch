# CrewAI-Based Chat System

This document explains the simplified CrewAI-based chat system that completely replaces the complex multi-endpoint agentic system.

## Overview

The new system consolidates the previous 3 complex endpoints into 2 clean, purpose-built endpoints using CrewAI flows:

### Before (Complex System) ❌
- `GET /chat:initiate/<uid>` - Start app-initiated chat
- `POST /chat/initiate:continue` - Continue app-initiated chat  
- `POST /chat/preference:continue` - Handle user-initiated chat with filter detection

### After (Simplified System) ✅
- `GET/POST /chat/app` - App-initiated hobby conversations
- `POST /chat/user` - User-initiated preference conversations

## Architecture

### CrewAI Agents
1. **Hobby Conversation Agent** - Handles app-initiated chats about user hobbies
2. **Dating Preference Agent** - Handles user-initiated chats and determines filtering needs
3. **Recommendation Filter Agent** - Filters recommendations based on user criteria

### Flow-Based Design
- Uses CrewAI Flows for better orchestration
- Automatic mode detection (FILTER vs CHAT)
- Cleaner separation of concerns
- Easier to maintain and extend

## API Endpoints

### 1. App-Initiated Chat (Hobbies)
```http
# Start new conversation
GET /chat/app?uid=user_123

# Continue conversation
POST /chat/app
Content-Type: application/json

{
    "uid": "user_id",
    "user_input": "user message",
    "history": [optional previous history]
}
```

**Purpose:** App initiates conversation about user's hobbies to improve matching algorithm.

### 2. User-Initiated Chat (Preferences/Filtering)
```http
POST /chat/user
Content-Type: application/json

{
    "uid": "user_id",
    "user_input": "user message",
    "history": [optional previous history]
}
```

**Purpose:** User asks questions about preferences or requests filtering of recommendations.

### Unified Response Format
```json
{
    "message": "AI response",
    "history": [{"role": "system", "content": "..."}, ...],
    "continue": true,
    "filter_applied": false,  // only for /chat/user when filter detected
    "recommendations": []     // only when filter is applied
}
```

## Examples

### App-Initiated Chat (Hobbies)
```javascript
// Start hobby conversation (app initiates)
const response = await fetch('/chat/app?uid=user123');
const data = await response.json();

console.log('App says:', data.message);

// Continue conversation
const continueResponse = await fetch('/chat/app', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        uid: 'user123',
        user_input: 'I love playing guitar and hiking',
        history: data.history
    })
});
```

### User-Initiated Chat (Preferences/Filtering)
```javascript
// User starts conversation about preferences
const response = await fetch('/chat/user', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        uid: 'user123',
        user_input: 'Show me matches only from Delhi'
    })
});

const data = await response.json();

// Automatically detects and applies filter if needed
if (data.filter_applied) {
    console.log('Filter applied:', data.recommendations);
}

// Continue the conversation
const continueResponse = await fetch('/chat/user', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        uid: 'user123',
        user_input: 'What do you think about my current matches?',
        history: data.history
    })
});
```

## Benefits

### 1. Simplified Architecture
- **Before**: 3 endpoints with complex routing logic
- **After**: 2 unified endpoints with clear purpose

### 2. Better Agent Coordination
- **Before**: Manual JSON parsing for mode detection
- **After**: CrewAI agents with proper tool integration

### 3. Cleaner Code
- **Before**: Duplicate chat continuation logic
- **After**: Unified flow-based handling

### 4. Easier Maintenance
- **Before**: Filter logic embedded in chat endpoints
- **After**: Clean separation via specialized agents

### 5. Better Error Handling
- **Before**: Complex error states across multiple endpoints
- **After**: Centralized error handling in flow

## Migration Guide

### 🚨 Breaking Changes - Frontend Updates Required

**Old endpoints have been completely removed and replaced with simplified ones.**

### Old System (REMOVED) ❌
```javascript
// App-initiated chat - REMOVED
const initResponse = await fetch(`/chat:initiate/${uid}`);
const continueResponse = await fetch('/chat/initiate:continue', {
    method: 'POST',
    body: JSON.stringify({uid, user_input, history})
});

// User-initiated chat - REMOVED 
const prefResponse = await fetch('/chat/preference:continue', {
    method: 'POST',
    body: JSON.stringify({uid, user_input, history})
});
```

### New System (SIMPLIFIED) ✅
```javascript
// App-initiated chat (hobbies)
const startResponse = await fetch(`/chat/app?uid=${uid}`);
const continueResponse = await fetch('/chat/app', {
    method: 'POST',
    body: JSON.stringify({uid, user_input, history})
});

// User-initiated chat (preferences/filtering)
const userResponse = await fetch('/chat/user', {
    method: 'POST',
    body: JSON.stringify({uid, user_input, history})
});
```

### Migration Steps

1. **Replace `/chat:initiate/<uid>`** → **`GET /chat/app?uid=<uid>`**
2. **Replace `/chat/initiate:continue`** → **`POST /chat/app`**
3. **Replace `/chat/preference:continue`** → **`POST /chat/user`**
4. **Remove `chat_type` parameter** - endpoints are now purpose-built
5. **Test with new simplified API**

### Why This Change?

✅ **Cleaner API** - Endpoints match business logic (app vs user initiated)  
✅ **Simpler Integration** - No need to specify chat types  
✅ **Better Performance** - Purpose-built endpoints  
✅ **Easier Maintenance** - Clear separation of concerns

## Configuration

The system uses the same configuration as the original:
- OpenAI API key from AWS Secrets Manager
- Prompts from `prompts.yaml`
- Database connections via `sqlite_adapter.py`
- Chat history storage in S3

## Troubleshooting

### CrewAI Not Available
If you see "CrewAI chat system not available", ensure:
1. `crewai` is installed: `pip install crewai`
2. `crewai_chat_system.py` is in the same directory
3. All dependencies are properly installed

### Import Errors
Check that all required packages are installed:
```bash
pip install crewai langchain langchain-community openai
```

### Flow Execution Errors
Enable verbose logging in CrewAI agents to debug flow execution issues.

## Performance Notes

- CrewAI flows may have slightly higher latency than direct LLM calls
- Agent initialization happens once at startup
- Tool integration provides better reliability for filter operations
- Consider implementing caching for frequently accessed user data 