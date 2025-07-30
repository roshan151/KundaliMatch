import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { config } from "../config/api";
import { useChatContext } from "../contexts/ChatContext";
import { useProfileContext } from "../contexts/ProfileContext";

interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
  sessionId?: string; // Track which session this message belongs to
  type?: 'chat:app' | 'chat:user' | 'session-separator'; // Track message type
}

interface ChatWithDestinyProps {
  userUID: string;
  onClose: () => void;
  showChatWindow: boolean;
  onUserSendMessage?: () => void;
  onFilterApplied?: (data: any) => void; // New prop for handling filter responses
  messages?: Message[];
  setMessages?: React.Dispatch<React.SetStateAction<Message[]>>;
  history?: any[];
  setHistory?: React.Dispatch<React.SetStateAction<any[]>>;
}

const ChatWithDestiny = ({ 
  userUID, 
  onClose, 
  showChatWindow, 
  onUserSendMessage,
  onFilterApplied, // New prop
  messages: propMessages,
  setMessages: propSetMessages,
  history: propHistory,
  setHistory: propSetHistory
}: ChatWithDestinyProps) => {
  const { 
    unifiedChatMessages, 
    setUnifiedChatMessages, 
    unifiedChatHistory, 
    setUnifiedChatHistory 
  } = useChatContext();
  
  const { refreshProfile } = useProfileContext();
  
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  // Use shared state if provided, otherwise fall back to unified context
  const messages = propMessages || unifiedChatMessages;
  const setMessages = propSetMessages || setUnifiedChatMessages;
  const history = propHistory || unifiedChatHistory;
  const setHistory = propSetHistory || setUnifiedChatHistory;
  
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    const scrollToBottom = () => {
      if (chatHistoryRef.current) {
        chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
      }
    };
    
    // Use setTimeout to ensure DOM has updated
    setTimeout(scrollToBottom, 100);
  }, [messages]);

  useEffect(() => {
    if (showChatWindow) {
      setIsChatOpen(true);
    }
  }, [showChatWindow]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      text: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    // Notify parent that user has sent a message
    if (onUserSendMessage) {
      onUserSendMessage();
    }

    try {
      const metadata = {
        uid: userUID,
        user_input: inputMessage,
        history: history
      };

      const response = await fetch("http://localhost:8040/chat:user", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(metadata),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data && data.message) {
        const responseMessage = {
          text: data.message,
          isUser: false,
          timestamp: new Date(),
        };
        
        setMessages(prev => [...prev, responseMessage]);

        if (data.history) {
          setHistory(data.history);
        } else {
          // Update history with the conversation
          setHistory(prev => [
            ...prev,
            { text: inputMessage, isUser: true },
            { text: data.message, isUser: false }
          ]);
        }

        // Check if filter was applied and handle recommendations
        if (data.filter_applied === true) {
          console.log('Filter applied in ChatWithDestiny, processing response:', data);
          
          // Trigger profile refresh to reflect new filters
          try {
            console.log('Refreshing user profile due to filter_applied=true in ChatWithDestiny');
            await refreshProfile(userUID);
            console.log('Profile refresh triggered successfully from ChatWithDestiny');
          } catch (error) {
            console.error('Error refreshing profile from ChatWithDestiny:', error);
          }
          
          // Call the parent callback if provided
          if (onFilterApplied) {
            console.log('Calling onFilterApplied callback with data:', data);
            onFilterApplied(data);
          }
        }

        // If this is the final message, mark chat as completed
        if (!data.continue) {
          sessionStorage.setItem('destinyChatCompleted', 'true');
          setTimeout(() => {
            setIsChatOpen(false);
            onClose();
          }, 2000);
        }
      }
    } catch (error) {
      console.error('Error in chat:', error);
      setMessages(prev => [...prev, {
        text: "I'm having trouble connecting right now. Please try again later.",
        isUser: false,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClose = () => {
    // Close the chat immediately
    setIsChatOpen(false);
    onClose();

    // Send exit message to server in the background (don't wait for response)
    if (userUID) {
      fetch('http://localhost:8040/chat:user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Origin': 'http://localhost:8080'
        },
        body: JSON.stringify({
          uid: userUID,
          user_input: "exit",
          history: messages.map(m => m.text)
        })
      })
      .catch(error => {
        console.error('Error handling chat exit:', error);
        // Error is logged but doesn't affect UI since chat is already closed
      });
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <Button
        onClick={() => setIsChatOpen(true)}
        className="w-24 h-24 sm:w-36 sm:h-36 rounded-full bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-lg"
      >
        <span className="text-4xl sm:text-6xl font-['Lavanderia']">D</span>
      </Button>

      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute bottom-32 right-0 bg-white rounded-lg shadow-xl w-80 sm:w-96"
          >
            <div className="p-4 border-b flex justify-between items-center bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-t-lg">
              <h3 className="font-['Lavanderia'] text-4xl">Destiny</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClose}
                className="h-8 w-8 hover:bg-indigo-500/20 text-white"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            
            <div 
              ref={chatHistoryRef}
              className="h-80 overflow-y-auto scroll-smooth p-4 space-y-4 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-gray-100 [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-thumb]:rounded-full"
            >
              {messages.length === 0 && (
                <div className="flex flex-col justify-center items-center h-[280px]">
                  <p className="text-gray-500 text-lg font-medium">Lets talk!</p>
                  <p className="text-gray-500 text-lg font-medium">About your</p>
                  <p className="text-gray-500 text-lg font-medium">matches and preferences!</p>
                </div>
              )}
              {messages.map((message, index) => {
                // Check if this is a session separator
                if (message.type === 'session-separator') {
                  return (
                    <div key={index} className="flex justify-center my-4">
                      <div className="flex items-center w-full">
                        <div className="flex-1 border-t border-gray-300"></div>
                        <div className="px-4 py-2 bg-gray-50 border border-gray-300 rounded-full">
                          <p className="text-xs text-gray-600 font-medium whitespace-nowrap">
                            {message.text}
                          </p>
                        </div>
                        <div className="flex-1 border-t border-gray-300"></div>
                      </div>
                    </div>
                  );
                }
                
                // Regular message rendering
                return (
                  <div 
                    key={index} 
                    className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[80%] rounded-lg p-3 ${
                      message.isUser 
                        ? 'bg-gradient-to-br from-indigo-500 to-indigo-600 text-white' 
                        : 'bg-gray-100 text-gray-900'
                    }`}>
                                             <p className="text-sm">{message.text}</p>
                       {/* Show message type indicator for debugging (optional) */}
                       {message.type && (
                         <p className="text-xs opacity-60 mt-1">
                           {message.type}
                         </p>
                       )}
                    </div>
                  </div>
                );
              })}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg p-3 text-gray-900">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
              {/* Invisible element to scroll to */}
              <div className="h-1" />
            </div>

            <div className="p-4 border-t">
              <div className="flex gap-2">
                <Input
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  className="flex-1 text-gray-900 placeholder:text-gray-500"
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={isLoading || !inputMessage.trim()}
                  className="bg-gradient-to-br from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ChatWithDestiny; 