import React, { createContext, useContext, useState, useRef, useEffect } from 'react';

interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
  sessionId?: string; // Track which session this message belongs to
  type?: 'chat:app' | 'chat:user' | 'session-separator'; // Track message type
}

interface SessionData {
  messages: Message[];
  history: any[];
  hasUserSentMessage: boolean;
  sessionId: string;
  loginTimestamp: number;
  hasMessages?: boolean;
}

interface UserChatData {
  [sessionId: string]: SessionData;
}

interface ChatContextType {
  unifiedChatMessages: Message[];
  setUnifiedChatMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  unifiedChatHistory: any[];
  setUnifiedChatHistory: React.Dispatch<React.SetStateAction<any[]>>;
  hasUserSentMessage: boolean;
  setHasUserSentMessage: React.Dispatch<React.SetStateAction<boolean>>;
  chatHistoryRef: React.RefObject<HTMLDivElement>;
  clearChatHistory: () => void;
  initializeUserSession: (userUID: string) => void;
  switchUser: (newUserUID: string) => void;
  addSessionSeparator: (type: 'login' | 'chat-type') => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUserUID, setCurrentUserUID] = useState<string>('');
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  
  // Generate session ID for current login
  const generateSessionId = () => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  // Helper function to check if there's a gap of more than 2 hours between timestamps
  const hasSignificantTimeGap = (earlierTimestamp: number, laterTimestamp: number): boolean => {
    const TWO_HOURS_IN_MS = 2 * 60 * 60 * 1000; // 2 hours in milliseconds
    return (laterTimestamp - earlierTimestamp) > TWO_HOURS_IN_MS;
  };
  
  // Helper function to format date in "mmm - dd", hh:mm format
  const formatChatSeparatorDate = (date: Date) => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    const month = months[date.getMonth()];
    const day = date.getDate();
    const dayWithSuffix = day + (day % 10 === 1 && day !== 11 ? 'st' : 
                                day % 10 === 2 && day !== 12 ? 'nd' : 
                                day % 10 === 3 && day !== 13 ? 'rd' : 'th');
    
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    
    return `${month} ${dayWithSuffix}, ${displayHours}:${minutes} ${ampm}`;
  };
  
  // Get user-specific storage key
  const getUserStorageKey = (userUID: string) => `destiny-chat-data-${userUID}`;
  
  // Load user's chat data from localStorage
  const loadUserChatData = (userUID: string): UserChatData => {
    try {
      const saved = localStorage.getItem(getUserStorageKey(userUID));
      return saved ? JSON.parse(saved) : {};
    } catch (error) {
      console.error('Error loading user chat data from localStorage:', error);
      return {};
    }
  };
  
  // Save user's chat data to localStorage
  const saveUserChatData = (userUID: string, data: UserChatData) => {
    try {
      localStorage.setItem(getUserStorageKey(userUID), JSON.stringify(data));
    } catch (error) {
      console.error('Error saving user chat data to localStorage:', error);
    }
  };
  
  // Initialize state with current user's current session data
  const [unifiedChatMessages, setUnifiedChatMessages] = useState<Message[]>([]);
  const [unifiedChatHistory, setUnifiedChatHistory] = useState<any[]>([]);
  const [hasUserSentMessage, setHasUserSentMessage] = useState(false);
  const [currentSessionHasMessages, setCurrentSessionHasMessages] = useState(false);
  
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  // Custom setter that handles session separator logic
  const setUnifiedChatMessagesWithSeparator = (
    value: Message[] | ((prev: Message[]) => Message[])
  ) => {
    setUnifiedChatMessages(prev => {
      const newMessages = typeof value === 'function' ? value(prev) : value;
      
      // Check if this is the first message being added to current session
      // and there are previous messages from other sessions
      if (
        !currentSessionHasMessages &&
        newMessages.length > prev.length &&
        prev.some(msg => msg.sessionId && msg.sessionId !== currentSessionId)
      ) {
        // Get the new message(s) being added
        const addedMessages = newMessages.slice(prev.length);
        const hasRealMessage = addedMessages.some(msg => msg.type !== 'session-separator');
        
        if (hasRealMessage) {
          // Find the timestamp of the last message from previous sessions
          const lastPreviousMessage = prev
            .filter(msg => msg.sessionId !== currentSessionId && msg.type !== 'session-separator')
            .pop();
          
          const currentDate = new Date();
          const currentTimestamp = currentDate.getTime();
          
          // Only add separator if there's a significant time gap (>2 hours) from last previous message
          let shouldAddSeparator = false;
          if (lastPreviousMessage) {
            // Convert timestamp to Date object if it's a string (from localStorage)
            const lastMessageDate = lastPreviousMessage.timestamp instanceof Date 
              ? lastPreviousMessage.timestamp 
              : new Date(lastPreviousMessage.timestamp);
            const lastMessageTimestamp = lastMessageDate.getTime();
            shouldAddSeparator = hasSignificantTimeGap(lastMessageTimestamp, currentTimestamp);
          } else {
            // If no previous messages found, check against session login timestamp
            // Load user data to get the most recent session timestamp
            const userData = loadUserChatData(currentUserUID);
            const sessionIds = Object.keys(userData).filter(id => id !== currentSessionId);
            if (sessionIds.length > 0) {
              const latestSessionTimestamp = Math.max(...sessionIds.map(id => userData[id].loginTimestamp));
              shouldAddSeparator = hasSignificantTimeGap(latestSessionTimestamp, currentTimestamp);
            }
          }
          
          if (shouldAddSeparator) {
            // Add current session separator before the new messages
            const separator: Message = {
              text: formatChatSeparatorDate(currentDate),
              isUser: false,
              timestamp: currentDate,
              sessionId: currentSessionId,
              type: 'session-separator'
            };
            
            // Insert separator before the new messages
            const withSeparator = [...prev, separator, ...addedMessages];
            setCurrentSessionHasMessages(true);
            return withSeparator;
          }
        }
      }
      
      // Mark session as having messages if new real messages are added
      if (newMessages.length > prev.length) {
        const addedMessages = newMessages.slice(prev.length);
        const hasRealMessage = addedMessages.some(msg => msg.type !== 'session-separator');
        if (hasRealMessage) {
          setCurrentSessionHasMessages(true);
        }
      }
      
      return newMessages;
    });
  };

  // Initialize user session
  const initializeUserSession = (userUID: string) => {
    if (userUID === currentUserUID) return; // Already initialized for this user
    
    console.log(`Initializing chat session for user: ${userUID}`);
    
    // Save current session data if we have a current user
    if (currentUserUID && currentSessionId) {
      const currentUserData = loadUserChatData(currentUserUID);
      currentUserData[currentSessionId] = {
        messages: unifiedChatMessages,
        history: unifiedChatHistory,
        hasUserSentMessage,
        sessionId: currentSessionId,
        loginTimestamp: Date.now(),
        hasMessages: currentSessionHasMessages
      };
      saveUserChatData(currentUserUID, currentUserData);
    }
    
    // Load new user's data
    const userData = loadUserChatData(userUID);
    const newSessionId = generateSessionId();
    
    // Combine all previous sessions messages for display
    const allPreviousMessages: Message[] = [];
    const sessionIds = Object.keys(userData).sort((a, b) => 
      userData[a].loginTimestamp - userData[b].loginTimestamp
    );
    
    // Filter sessions that have actual messages
    const sessionsWithMessages = sessionIds.filter(sessionId => 
      userData[sessionId].messages.length > 0
    );
    
    sessionsWithMessages.forEach((sessionId, index) => {
      const sessionData = userData[sessionId];
      
      // Add session separator only if:
      // 1. This is not the first session with messages
      // 2. There's a time gap of more than 2 hours from the previous session
      if (index > 0) {
        const previousSessionId = sessionsWithMessages[index - 1];
        const previousSessionData = userData[previousSessionId];
        const currentSessionTimestamp = sessionData.loginTimestamp;
        const previousSessionTimestamp = previousSessionData.loginTimestamp;
        
        // Only add separator if there's a significant time gap (>2 hours)
        if (hasSignificantTimeGap(previousSessionTimestamp, currentSessionTimestamp)) {
          const sessionDate = new Date(sessionData.loginTimestamp);
          allPreviousMessages.push({
            text: formatChatSeparatorDate(sessionDate),
            isUser: false,
            timestamp: sessionDate,
            sessionId: sessionId,
            type: 'session-separator'
          });
        }
      }
      
      // Convert timestamp strings back to Date objects for messages loaded from localStorage
      const messagesWithProperDates = sessionData.messages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp)
      }));
      allPreviousMessages.push(...messagesWithProperDates);
    });
    
    // Don't add current session separator yet - wait until there are actual messages
    
    setCurrentUserUID(userUID);
    setCurrentSessionId(newSessionId);
    setUnifiedChatMessages(allPreviousMessages);
    setUnifiedChatHistory([]);
    setHasUserSentMessage(false);
    setCurrentSessionHasMessages(false);
  };
  
  // Switch to different user (security: clear everything)
  const switchUser = (newUserUID: string) => {
    console.log(`Switching from user ${currentUserUID} to ${newUserUID}`);
    
    // Save current user's session data
    if (currentUserUID && currentSessionId) {
      const currentUserData = loadUserChatData(currentUserUID);
      currentUserData[currentSessionId] = {
        messages: unifiedChatMessages,
        history: unifiedChatHistory,
        hasUserSentMessage,
        sessionId: currentSessionId,
        loginTimestamp: Date.now(),
        hasMessages: currentSessionHasMessages
      };
      saveUserChatData(currentUserUID, currentUserData);
    }
    
    // Clear current state completely for security
    setUnifiedChatMessages([]);
    setUnifiedChatHistory([]);
    setHasUserSentMessage(false);
    setCurrentSessionHasMessages(false);
    setCurrentUserUID('');
    setCurrentSessionId('');
    
    // Initialize new user
    initializeUserSession(newUserUID);
  };
  
  // Add session separator for different chat types
  const addSessionSeparator = (type: 'login' | 'chat-type') => {
    const currentDate = new Date();
    const separatorText = formatChatSeparatorDate(currentDate);
      
    const separator: Message = {
      text: separatorText,
      isUser: false,
      timestamp: currentDate,
      sessionId: currentSessionId,
      type: 'session-separator'
    };
    
    setUnifiedChatMessages(prev => [...prev, separator]);
  };

  // Persist current session data whenever messages change
  useEffect(() => {
    if (currentUserUID && currentSessionId && unifiedChatMessages.length > 0) {
      const userData = loadUserChatData(currentUserUID);
      userData[currentSessionId] = {
        messages: unifiedChatMessages,
        history: unifiedChatHistory,
        hasUserSentMessage,
        sessionId: currentSessionId,
        loginTimestamp: userData[currentSessionId]?.loginTimestamp || Date.now(),
        hasMessages: currentSessionHasMessages
      };
      saveUserChatData(currentUserUID, userData);
    }
  }, [unifiedChatMessages, unifiedChatHistory, hasUserSentMessage, currentSessionHasMessages, currentUserUID, currentSessionId]);

  // Effect to scroll to bottom when chat history changes
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [unifiedChatMessages]);

  // Function to clear chat history and user data (for logout)
  const clearChatHistory = () => {
    // Save current session before clearing
    if (currentUserUID && currentSessionId) {
      const userData = loadUserChatData(currentUserUID);
      userData[currentSessionId] = {
        messages: unifiedChatMessages,
        history: unifiedChatHistory,
        hasUserSentMessage,
        sessionId: currentSessionId,
        loginTimestamp: Date.now(),
        hasMessages: currentSessionHasMessages
      };
      saveUserChatData(currentUserUID, userData);
    }
    
    // Clear current state
    setUnifiedChatMessages([]);
    setUnifiedChatHistory([]);
    setHasUserSentMessage(false);
    setCurrentSessionHasMessages(false);
    setCurrentUserUID('');
    setCurrentSessionId('');
    
    // Clear old sessionStorage items (legacy cleanup)
    try {
      sessionStorage.removeItem('destiny-chat-messages');
      sessionStorage.removeItem('destiny-chat-history');
      sessionStorage.removeItem('destinyUserHasChatted');
      sessionStorage.removeItem('destinyChatCompleted');
      sessionStorage.removeItem('destinyChatDismissed');
      
      // Clear ChatWithDestiny usage tracking for all users
      const keys = Object.keys(sessionStorage);
      keys.forEach(key => {
        if (key.startsWith('destinyWindowChatUsed_')) {
          sessionStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.error('Error clearing legacy chat data from sessionStorage:', error);
    }
  };

  const value = {
    unifiedChatMessages,
    setUnifiedChatMessages: setUnifiedChatMessagesWithSeparator,
    unifiedChatHistory,
    setUnifiedChatHistory,
    hasUserSentMessage,
    setHasUserSentMessage,
    chatHistoryRef,
    clearChatHistory,
    initializeUserSession,
    switchUser,
    addSessionSeparator,
  };

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}; 