import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { ArrowLeft, Send, User, Paperclip, X, Image as ImageIcon } from "lucide-react";
import { config } from "../config/api";
import { Client as ConversationsClient } from '@twilio/conversations';
import { useS3Assets } from "../hooks/useS3Assets";

interface Message {
  sid: string;
  body: string;
  author: string;
  timestamp: Date;
  media?: {
    filename: string;
    contentType: string;
    size: number;
    url?: string;
  };
}

interface UserInfo {
  name: string;
  profilePicture?: string;
}

interface UserQuestions {
  Question1?: {
    Question: string;
    Answer: string;
  };
  Question2?: {
    Question: string;
    Answer: string;
  };
  Question3?: {
    Question: string;
    Answer: string;
  };
}

const Chat = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { uid } = useParams();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const { assets } = useS3Assets();
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [chatClient, setChatClient] = useState<any>(null);
  const [conversation, setConversation] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [userQuestions, setUserQuestions] = useState<UserQuestions | null>(null);
  const [showUserProfile, setShowUserProfile] = useState(false);

  // Helper function to detect correct content type
  const getCorrectContentType = (originalContentType: string, filename: string, url?: string): string => {
    if (originalContentType && originalContentType !== 'application/octet-stream') {
      return originalContentType;
    }
    
    // Enhanced file extension detection
    if (filename && filename !== 'attachment') {
      const lowercaseFilename = filename.toLowerCase();
      
      // Image types
      if (lowercaseFilename.match(/\.(jpg|jpeg)$/)) {
        return 'image/jpeg';
      } else if (lowercaseFilename.match(/\.png$/)) {
        return 'image/png';
      } else if (lowercaseFilename.match(/\.gif$/)) {
        return 'image/gif';
      } else if (lowercaseFilename.match(/\.webp$/)) {
        return 'image/webp';
      } else if (lowercaseFilename.match(/\.svg$/)) {
        return 'image/svg+xml';
      } else if (lowercaseFilename.match(/\.bmp$/)) {
        return 'image/bmp';
      } else if (lowercaseFilename.match(/\.tiff?$/)) {
        return 'image/tiff';
      } else if (lowercaseFilename.match(/\.ico$/)) {
        return 'image/x-icon';
      }
      
      // Video types
      else if (lowercaseFilename.match(/\.mp4$/)) {
        return 'video/mp4';
      } else if (lowercaseFilename.match(/\.webm$/)) {
        return 'video/webm';
      } else if (lowercaseFilename.match(/\.mov$/)) {
        return 'video/quicktime';
      } else if (lowercaseFilename.match(/\.avi$/)) {
        return 'video/x-msvideo';
      } else if (lowercaseFilename.match(/\.mkv$/)) {
        return 'video/x-matroska';
      } else if (lowercaseFilename.match(/\.flv$/)) {
        return 'video/x-flv';
      } else if (lowercaseFilename.match(/\.wmv$/)) {
        return 'video/x-ms-wmv';
      } else if (lowercaseFilename.match(/\.m4v$/)) {
        return 'video/x-m4v';
      }
      
      // Audio types
      else if (lowercaseFilename.match(/\.mp3$/)) {
        return 'audio/mpeg';
      } else if (lowercaseFilename.match(/\.wav$/)) {
        return 'audio/wav';
      } else if (lowercaseFilename.match(/\.ogg$/)) {
        return 'audio/ogg';
      } else if (lowercaseFilename.match(/\.aac$/)) {
        return 'audio/aac';
      } else if (lowercaseFilename.match(/\.flac$/)) {
        return 'audio/flac';
      } else if (lowercaseFilename.match(/\.m4a$/)) {
        return 'audio/mp4';
      }
      
      // Document types
      else if (lowercaseFilename.match(/\.pdf$/)) {
        return 'application/pdf';
      } else if (lowercaseFilename.match(/\.docx?$/)) {
        return lowercaseFilename.endsWith('.docx') ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'application/msword';
      } else if (lowercaseFilename.match(/\.xlsx?$/)) {
        return lowercaseFilename.endsWith('.xlsx') ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'application/vnd.ms-excel';
      } else if (lowercaseFilename.match(/\.pptx?$/)) {
        return lowercaseFilename.endsWith('.pptx') ? 'application/vnd.openxmlformats-officedocument.presentationml.presentation' : 'application/vnd.ms-powerpoint';
      } else if (lowercaseFilename.match(/\.txt$/)) {
        return 'text/plain';
      } else if (lowercaseFilename.match(/\.rtf$/)) {
        return 'application/rtf';
      }
      
      // Archive types
      else if (lowercaseFilename.match(/\.zip$/)) {
        return 'application/zip';
      } else if (lowercaseFilename.match(/\.rar$/)) {
        return 'application/vnd.rar';
      } else if (lowercaseFilename.match(/\.7z$/)) {
        return 'application/x-7z-compressed';
      } else if (lowercaseFilename.match(/\.tar\.gz$/)) {
        return 'application/gzip';
      }
      
      // Code/text files
      else if (lowercaseFilename.match(/\.(js|jsx)$/)) {
        return 'text/javascript';
      } else if (lowercaseFilename.match(/\.(ts|tsx)$/)) {
        return 'text/typescript';
      } else if (lowercaseFilename.match(/\.css$/)) {
        return 'text/css';
      } else if (lowercaseFilename.match(/\.html?$/)) {
        return 'text/html';
      } else if (lowercaseFilename.match(/\.json$/)) {
        return 'application/json';
      } else if (lowercaseFilename.match(/\.xml$/)) {
        return 'application/xml';
      } else if (lowercaseFilename.match(/\.csv$/)) {
        return 'text/csv';
      }
    }
    
    // Try to detect by URL if available
    if (url) {
      const urlLower = url.toLowerCase();
      
      // Check for Twilio media URLs - they often contain media IDs that we can use
      if (urlLower.includes('media.') && urlLower.includes('twilio.com')) {
        // For Twilio media, we need to make an educated guess based on context
        // Since we know this came from a file upload that was validated as an image/video/audio
        // and Twilio commonly strips filenames, we can try a different approach
        
        // Try to extract any file extension hints from the URL query parameters or path
        const urlParts = url.split(/[?&]/);
        for (const part of urlParts) {
          if (part.includes('.jpg') || part.includes('.jpeg')) {
            return 'image/jpeg';
          } else if (part.includes('.png')) {
            return 'image/png';
          } else if (part.includes('.gif')) {
            return 'image/gif';
          } else if (part.includes('.webp')) {
            return 'image/webp';
          } else if (part.includes('.mp4')) {
            return 'video/mp4';
          } else if (part.includes('.webm')) {
            return 'video/webm';
          }
        }
        
        // If no specific type found in URL, make educated guess based on common Twilio usage
        // Most media uploads to Twilio chat are images, so default to image for unknown types
        return 'image/jpeg';
      }
      
      // General URL pattern detection
      if (urlLower.includes('image') || urlLower.includes('photo') || urlLower.includes('pic')) {
        return 'image/jpeg'; // Default image type
      } else if (urlLower.includes('video') || urlLower.includes('movie')) {
        return 'video/mp4'; // Default video type
      } else if (urlLower.includes('audio') || urlLower.includes('sound')) {
        return 'audio/mpeg'; // Default audio type
      }
    }
    
    // Default to image/jpeg if we suspect it's an image based on filename patterns
    if (filename && (filename.includes('image') || filename.includes('photo') || filename.includes('pic') || filename.includes('img'))) {
      return 'image/jpeg';
    }
    
    // Final fallback
    return originalContentType || 'application/octet-stream';
  };

  // Helper function to determine if file type is supported for preview
  const isPreviewableType = (contentType: string): boolean => {
    return contentType.startsWith('image/') || 
           contentType.startsWith('video/') || 
           contentType.startsWith('audio/') ||
           contentType === 'application/pdf' ||
           contentType.startsWith('text/');
  };

  // Helper function to get file type category
  const getFileTypeCategory = (contentType: string): 'image' | 'video' | 'audio' | 'document' | 'archive' | 'code' | 'other' => {
    if (!contentType) {
      return 'other';
    }
    
    if (contentType.startsWith('image/')) {
      return 'image';
    }
    if (contentType.startsWith('video/')) {
      return 'video';
    }
    if (contentType.startsWith('audio/')) {
      return 'audio';
    }
    if (contentType.includes('pdf') || contentType.includes('document') || contentType.includes('word') || contentType.includes('excel') || contentType.includes('powerpoint') || contentType.startsWith('text/')) {
      return 'document';
    }
    if (contentType.includes('zip') || contentType.includes('rar') || contentType.includes('archive') || contentType.includes('compressed')) {
      return 'archive';
    }
    if (contentType.includes('javascript') || contentType.includes('typescript') || contentType.includes('css') || contentType.includes('html') || contentType.includes('json') || contentType.includes('xml')) {
      return 'code';
    }
    
    return 'other';
  };

  // Helper function to validate file before upload
  const validateFile = (file: File): { valid: boolean; error?: string; correctedType?: string } => {
    // Size validation
    const maxSize = 25 * 1024 * 1024; // 25MB
    if (file.size > maxSize) {
      return { valid: false, error: 'File size must be less than 25MB' };
    }

    // Type validation and correction
    let correctedType = file.type;
    if (!file.type || file.type === 'application/octet-stream') {
      correctedType = getCorrectContentType(file.type, file.name);
    }

    const allowedTypes = [
      // Images
      'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml', 'image/bmp', 'image/tiff',
      // Videos
      'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/x-flv', 'video/x-ms-wmv', 'video/x-m4v',
      // Audio
      'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/aac', 'audio/flac', 'audio/mp4',
      // Documents
      'application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ];

    if (!allowedTypes.includes(correctedType)) {
      return { 
        valid: false, 
        error: `File type "${correctedType}" is not supported. Please upload images, videos, audio files, or documents.` 
      };
    }

    return { valid: true, correctedType };
  };

  // Helper function to format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-scroll function
  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  };

  // Check if user is near bottom of chat
  const isNearBottom = () => {
    if (!messagesContainerRef.current) return true;
    
    const container = messagesContainerRef.current;
    const threshold = 100; // pixels from bottom
    
    return (
      container.scrollTop + container.clientHeight >= 
      container.scrollHeight - threshold
    );
  };

  // Scroll to bottom only if user is near bottom (to not interrupt reading)
  const conditionalScrollToBottom = () => {
    if (isNearBottom()) {
      scrollToBottom();
    }
  };

  const [isBlocked, setIsBlocked] = useState(false);

  useEffect(() => {
    // First, try to use cached data from navigation state
    const cachedUserData = location.state as { 
      userName?: string; 
      userProfilePicture?: string; 
      isBlocked?: boolean;
      Question1?: { Question: string; Answer: string };
      Question2?: { Question: string; Answer: string };
      Question3?: { Question: string; Answer: string };
    } | null;
    
    if (cachedUserData?.userName) {
      setUserInfo({
        name: cachedUserData.userName,
        profilePicture: cachedUserData.userProfilePicture || null
      });
    }

    // Set questions data from navigation state
    if (cachedUserData && (cachedUserData.Question1 || cachedUserData.Question2 || cachedUserData.Question3)) {
      setUserQuestions({
        Question1: cachedUserData.Question1,
        Question2: cachedUserData.Question2,
        Question3: cachedUserData.Question3
      });
    }

    // Set blocked status from navigation state
    if (cachedUserData?.isBlocked !== undefined) {
      setIsBlocked(cachedUserData.isBlocked);
    }

    const fetchUserProfile = async () => {
      // Skip API fetch if we already have cached data
      if (cachedUserData?.userName && cachedUserData?.userProfilePicture) {
        return;
      }
      
      if (!uid) return;
      
      try {
        const response = await fetch(`${config.URL}${config.ENDPOINTS.GET_PROFILE}/${uid}`, {
          method: 'GET',
        });
        
        if (response.ok) {
          const data = await response.json();
          
          setUserInfo({
            name: data.NAME || data.name || 'Unknown User',
            profilePicture: data.images && data.images.length > 0 ? data.images[0] : null
          });
        }
      } catch (error) {
        console.error('Error fetching user profile:', error);
        // Only set fallback if we don't have cached data
        if (!cachedUserData?.userName) {
          setUserInfo({
            name: 'Unknown User'
          });
        }
      }
    };

    const initializeChat = async () => {
      try {
        // Get current user's UID from localStorage with fallback options
        let currentUserUID = localStorage.getItem('userUID');
        
        // If userUID is not found, try to get it from userData
        if (!currentUserUID) {
          const userData = localStorage.getItem('userData');
          if (userData) {
            try {
              const parsedUserData = JSON.parse(userData);
              currentUserUID = parsedUserData.uid;
              console.log('Retrieved userUID from userData:', currentUserUID);
              
              // Store it back in userUID for future use
              if (currentUserUID) {
                localStorage.setItem('userUID', currentUserUID);
              }
            } catch (error) {
              console.error('Error parsing userData from localStorage:', error);
            }
          }
        }
        
        // Final check for userUID
        if (!currentUserUID) {
          console.error('Debug info - localStorage contents:');
          console.error('userUID:', localStorage.getItem('userUID'));
          console.error('userData:', localStorage.getItem('userData'));
          console.error('isLoggedIn:', localStorage.getItem('isLoggedIn'));
          const errorMsg = 'Current user ID not found in localStorage. Please try logging in again.';
          setAuthError(errorMsg);
          throw new Error(errorMsg);
        }
        
        if (!uid) {
          throw new Error('Target user ID not found in URL parameters');
        }
        
        console.log('Initializing chat with currentUserUID:', currentUserUID, 'targetUID:', uid);

        // Show UI immediately while initializing chat in background
        setIsInitializing(false);
        setIsLoading(false);

        // Make API calls in parallel for faster initialization
        const [tokenResponse, conversationResponse] = await Promise.all([
          fetch(`${config.URL}/e2echat:token/${currentUserUID}`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'Content-Type': 'application/json',
            }
          }),
          fetch(`${config.URL}/e2echat:conversation`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              uid1: currentUserUID,
              uid2: uid
            })
          })
        ]);

        if (!tokenResponse.ok) {
          throw new Error(`Failed to get access token: ${tokenResponse.status}`);
        }
        if (!conversationResponse.ok) {
          throw new Error(`Failed to get conversation: ${conversationResponse.status}`);
        }

        const [tokenData, conversationData] = await Promise.all([
          tokenResponse.json(),
          conversationResponse.json()
        ]);

        const { token } = tokenData;
        const { conversation_sid } = conversationData;
        console.log('Got token and conversation_sid:', { token: !!token, conversation_sid });

        // Initialize Twilio Chat client with optimized timeout
        let chatClient;
        try {
          console.log('Creating Twilio Conversations client...');
          chatClient = await ConversationsClient.create(token);
          console.log('Client created, connection state:', chatClient.connectionState);
          
          // Wait for the client to be fully initialized with reduced timeout
          if (chatClient.connectionState !== 'connected') {
            console.log('Waiting for client to connect...');
            await new Promise((resolve, reject) => {
              const timeout = setTimeout(() => {
                console.warn('Client connection timeout - proceeding anyway');
                // Don't reject, just resolve and let the app continue
                resolve(true);
              }, 5000); // Reduced to 5 seconds for faster UX
              
              chatClient.on('stateChanged', (state) => {
                console.log('Client state changed to:', state);
                if (state === 'connected') {
                  console.log('Client successfully connected!');
                  clearTimeout(timeout);
                  resolve(true);
                }
              });
              
              chatClient.on('connectionError', (error) => {
                console.error('Connection error:', error);
                clearTimeout(timeout);
                // Don't reject on connection error, let the app continue
                resolve(true);
              });
              
              // If already connected, resolve immediately
              if (chatClient.connectionState === 'connected') {
                console.log('Client already connected!');
                clearTimeout(timeout);
                resolve(true);
              }
            });
          } else {
            console.log('Client already connected!');
          }
          
          setChatClient(chatClient);
        } catch (error) {
          console.error("Chat initialization error:", error);
          // Don't throw error, just log it and continue - user can still see the UI
          console.warn("Continuing with limited chat functionality");
        }

        // Get conversation (only if chatClient is available)
        let conversation;
        if (chatClient) {
          try {
            // Get the conversation using the SID
            console.log('Attempting to get conversation with SID:', conversation_sid);
            conversation = await chatClient.getConversationBySid(conversation_sid);
            console.log('Successfully retrieved conversation:', conversation);
          } catch (error) {
            console.error('Error getting conversation:', error);
            
            // If conversation doesn't exist, try to create a new one
            try {
              console.log('Attempting to create a new conversation...');
              conversation = await chatClient.createConversation({
                uniqueName: `chat_${currentUserUID}_${uid}`,
                friendlyName: `Chat between users`
              });
              
              // Add both users to the conversation
              await conversation.add(currentUserUID);
              await conversation.add(uid);
              
              console.log('Successfully created new conversation:', conversation);
            } catch (createError) {
              console.error('Error creating conversation:', createError);
              console.warn('Continuing without conversation - limited functionality');
            }
          }
          
          if (conversation) {
            setConversation(conversation);
            
            // Debug: Log available methods on conversation object
            console.log('Available conversation methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(conversation)));
            console.log('Conversation object:', conversation);
            
            // Check if there are any media-related methods
            const conversationMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(conversation));
            const mediaMethods = conversationMethods.filter(method => 
              method.toLowerCase().includes('media') || 
              method.toLowerCase().includes('attachment') ||
              method.toLowerCase().includes('file')
            );
            console.log('Media-related methods on conversation:', mediaMethods);
          }
        }
        
        // Set up message listener and load messages (only if conversation exists)
        if (conversation) {
          // Set up message listener with optimized processing
          conversation.on('messageAdded', async (message: any) => {
            console.log('New message received:', message);
            console.log('Message attachedMedia:', message.attachedMedia);
            console.log('Message media:', message.media);
            console.log('Full new message object:', message);
            console.log('New message body:', message.body);
            console.log('New message attributes:', message.attributes);
            console.log('All new message properties:', Object.keys(message));
            
            // Check if message has a state property with the actual data
            if (message.state) {
              console.log('Message state:', message.state);
              console.log('State body:', message.state.body);
              console.log('State attachedMedia:', message.state.attachedMedia);
              console.log('State media:', message.state.media);
            }
            
            // Check if message has other data properties
            if (message.data) {
              console.log('Message data:', message.data);
            }
            
            // Try to access message properties through getters
            try {
              console.log('Message.body getter:', message.body);
              console.log('Message.attachedMedia getter:', message.attachedMedia);
              console.log('Message.media getter:', message.media);
              console.log('Message.author getter:', message.author);
              console.log('Message.timestamp getter:', message.timestamp);
              console.log('Message.sid getter:', message.sid);
              
              // Try the specific media getter methods only if there's attached media
              if (message.attachedMedia && message.attachedMedia.length > 0 && typeof message.getTemporaryContentUrlsForAttachedMedia === 'function') {
                console.log('Trying getTemporaryContentUrlsForAttachedMedia...');
                const mediaSids = message.attachedMedia.map(media => media.sid).filter(sid => sid);
                if (mediaSids.length > 0) {
                  message.getTemporaryContentUrlsForAttachedMedia(mediaSids).then(urls => {
                    console.log('Attached media URLs:', urls);
                  }).catch(err => console.log('getTemporaryContentUrlsForAttachedMedia error:', err));
                }
              }
              
              if (typeof message.media === 'function') {
                console.log('Message.media is a function, calling it...');
                const mediaResult = message.media();
                console.log('Message.media() result:', mediaResult);
              }
              
            } catch (error) {
              console.error('Error accessing message getters:', error);
            }
            
            // Check what methods are available on the message object
            const messageMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(message));
            console.log('Available message methods:', messageMethods);
            
            // Look for getter methods
            const getterMethods = messageMethods.filter(method => 
              method.startsWith('get') || 
              method.includes('body') || 
              method.includes('media') || 
              method.includes('attachment')
            );
            console.log('Potential getter methods:', getterMethods);
            
            // Process media asynchronously to not block UI
            let mediaInfo = null;
            
            // Use the proper Twilio Conversations API getters
            console.log('Using Twilio getter methods for message data');
            console.log('Message attachedMedia:', message.attachedMedia);
            console.log('Message media:', message.media);
            
            // Try to get media using the proper API methods
            // First check if message has attachedMedia to get the SIDs
            if (message.attachedMedia && message.attachedMedia.length > 0 && typeof message.getTemporaryContentUrlsForAttachedMedia === 'function') {
              console.log('Getting media URLs using getTemporaryContentUrlsForAttachedMedia...');
              try {
                // Extract media SIDs from attachedMedia
                const mediaSids = message.attachedMedia.map(media => media.sid).filter(sid => sid);
                console.log('Media SIDs:', mediaSids);
                
                if (mediaSids.length > 0) {
                  const mediaUrls = await message.getTemporaryContentUrlsForAttachedMedia(mediaSids);
                  console.log('Got media URLs:', mediaUrls);
                  
                  if (mediaUrls && mediaUrls.length > 0) {
                                      const mediaUrl = mediaUrls[0];
                  const mediaObject = message.attachedMedia[0];
                  
                  // Better content type detection
                  const contentType = getCorrectContentType(
                    mediaObject.contentType || '', 
                    mediaObject.filename || '',
                    mediaUrl.url || mediaUrl
                  );
                  
                  mediaInfo = {
                    filename: mediaObject.filename || 'attachment',
                    contentType: contentType,
                    size: mediaObject.size || 0,
                    url: mediaUrl.url || mediaUrl
                  };
                  }
                }
              } catch (error) {
                console.error('Error getting media URLs:', error);
              }
            }
            
            // Fallback: Check for attachedMedia property
            if (!mediaInfo) {
              const attachedMedia = message.attachedMedia;
              if (attachedMedia && attachedMedia.length > 0) {
                console.log('Processing attachedMedia property...');
                const media = attachedMedia[0];
                console.log('Media object:', media);
              
                try {
                  const mediaUrl = await media.getContentTemporaryUrl();
                  console.log('Got media URL:', mediaUrl);
                  
                  const detectedContentType = getCorrectContentType(media.contentType || '', media.filename || '', mediaUrl);
                  
                  mediaInfo = {
                    filename: media.filename || 'attachment',
                    contentType: detectedContentType,
                    size: media.size || 0,
                    url: mediaUrl
                  };
                } catch (error) {
                  console.error('Error getting media URL from attachedMedia:', error);
                  
                  // Fallback: try to get URL directly from media object
                  try {
                    mediaInfo = {
                      filename: media.filename || 'attachment',
                      contentType: getCorrectContentType(media.contentType || '', media.filename || '', media.url || null),
                      size: media.size || 0,
                      url: media.url || null
                    };
                    console.log('Created fallback mediaInfo:', mediaInfo);
                  } catch (fallbackError) {
                    console.error('Fallback media processing failed:', fallbackError);
                  }
                }
              }
            }
            
            // Additional fallback: Check for media property
            if (!mediaInfo) {
              const mediaProperty = message.media;
              if (mediaProperty && mediaProperty.length > 0) {
                console.log('Processing media property...');
                const media = mediaProperty[0];
                console.log('Media object from media property:', media);
                
                try {
                  const mediaUrl = await media.getContentTemporaryUrl();
                  console.log('Got media URL from media property:', mediaUrl);
                  
                  mediaInfo = {
                    filename: media.filename || 'attachment',
                    contentType: getCorrectContentType(media.contentType || '', media.filename || '', mediaUrl),
                    size: media.size || 0,
                    url: mediaUrl
                  };
                  console.log('Created mediaInfo from media property:', mediaInfo);
                } catch (error) {
                  console.error('Error getting media URL from media property:', error);
                }
              }
            }
            
            const newMessage = {
              sid: message.sid,
              body: message.body || '',
              author: message.author,
              timestamp: message.timestamp ? new Date(message.timestamp) : new Date(),
              media: mediaInfo
            };
            
            console.log('Final processed message:', newMessage);
            
            // Prevent duplicate messages and update state
            setMessages(prev => {
              const messageExists = prev.some(msg => msg.sid === message.sid);
              if (messageExists) {
                console.log('Message already exists, skipping:', message.sid);
                return prev;
              }
              console.log('Adding new message to state');
              return [...prev, newMessage];
            });
            
            // Auto-scroll to bottom when new message arrives
            setTimeout(conditionalScrollToBottom, 100);
          });

          // Load existing messages in background (don't block UI)
          setIsLoadingMessages(true);
          conversation.getMessages().then(async (existingMessages) => {
            console.log('Loading existing messages:', existingMessages.items.length);
            
            // Process messages in batches for better performance
            const batchSize = 10;
            const messages = existingMessages.items;
            const processedMessages = [];
            
            for (let i = 0; i < messages.length; i += batchSize) {
              const batch = messages.slice(i, i + batchSize);
              const batchProcessed = await Promise.all(
                batch.map(async (message: any) => {
                  let mediaInfo = null;
                  
                  console.log('Processing existing message:', message.sid, 'attachedMedia:', message.attachedMedia, 'media:', message.media);
                  
                  // Try to get the actual message data for existing messages too
                  let actualMessage = message;
                  if (message.state && typeof message.state === 'object') {
                    actualMessage = message.state;
                    console.log('Using existing message.state as actual message data');
                  }
                  console.log('Full message object:', message);
                  console.log('Message body:', message.body);
                  console.log('Message attributes:', message.attributes);
                  console.log('All message properties:', Object.keys(message));
                  
                  // Check if existing message has state property
                  if (message.state) {
                    console.log('Existing message state:', message.state);
                  }
                  
                  // Check for attachedMedia (newer API)
                  const attachedMedia = actualMessage.attachedMedia || message.attachedMedia;
                  if (attachedMedia && attachedMedia.length > 0) {
                    console.log('Processing existing message attachedMedia...');
                    const media = attachedMedia[0];
                    try {
                      const mediaUrl = await media.getContentTemporaryUrl();
                      console.log('Got existing message media URL:', mediaUrl);
                      
                      mediaInfo = {
                        filename: media.filename || 'attachment',
                        contentType: getCorrectContentType(media.contentType || '', media.filename || '', mediaUrl),
                        size: media.size || 0,
                        url: mediaUrl
                      };
                    } catch (error) {
                      console.error('Error getting media URL for existing message:', error);
                      
                      // Fallback: try to get URL directly from media object
                      try {
                        mediaInfo = {
                          filename: media.filename || 'attachment',
                          contentType: getCorrectContentType(media.contentType || '', media.filename || '', media.url || null),
                          size: media.size || 0,
                          url: media.url || null
                        };
                        console.log('Created fallback mediaInfo for existing message:', mediaInfo);
                      } catch (fallbackError) {
                        console.error('Fallback media processing failed for existing message:', fallbackError);
                      }
                    }
                  }
                  // Check for media property (alternative API)
                  const mediaProperty = actualMessage.media || message.media;
                  if (!mediaInfo && mediaProperty && mediaProperty.length > 0) {
                    console.log('Processing existing message media property...');
                    const media = mediaProperty[0];
                    try {
                      const mediaUrl = await media.getContentTemporaryUrl();
                      console.log('Got existing message media URL from media property:', mediaUrl);
                      
                      mediaInfo = {
                        filename: media.filename || 'attachment',
                        contentType: getCorrectContentType(media.contentType || '', media.filename || '', mediaUrl),
                        size: media.size || 0,
                        url: mediaUrl
                      };
                    } catch (error) {
                      console.error('Error getting media URL from media property for existing message:', error);
                    }
                  }
                  
                  const processedMessage = {
                    sid: actualMessage.sid || message.sid,
                    body: actualMessage.body || message.body || '',
                    author: actualMessage.author || message.author,
                    timestamp: actualMessage.timestamp ? new Date(actualMessage.timestamp) : 
                              (message.timestamp ? new Date(message.timestamp) : new Date()),
                    media: mediaInfo
                  };
                  
                  console.log('Processed existing message:', processedMessage);
                  return processedMessage;
                })
              );
              processedMessages.push(...batchProcessed);
            }
            
            setMessages(processedMessages);
            setIsLoadingMessages(false);
            console.log('Loaded', processedMessages.length, 'existing messages');
          }).catch(error => {
            console.error('Error loading existing messages:', error);
            setIsLoadingMessages(false);
          });
        }
      } catch (err) {
        console.error('Chat initialization error:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to initialize chat';
        
        // If it's an auth error, set authError instead of general error
        if (errorMessage.includes('Current user ID not found')) {
          setAuthError(errorMessage);
        } else {
          setError(errorMessage);
        }
        setIsLoading(false);
      }
    };

    fetchUserProfile();
    initializeChat();

    return () => {
      if (chatClient) {
        chatClient.shutdown();
      }
    };
  }, [uid]);

  const handleSendMessage = async () => {
    if ((!newMessage.trim() && !selectedFile) || !conversation || isSending) return;

    setIsSending(true);
    try {
      if (selectedFile) {
        console.log('Sending media file:', selectedFile);
        console.log('File details:', {
          name: selectedFile.name,
          type: selectedFile.type,
          size: selectedFile.size
        });
        
        // Ensure the file has the correct MIME type (selectedFile should already be corrected from handleFileSelect)
        let fileWithCorrectType = selectedFile;
        
        // Double-check MIME type detection
        if (!selectedFile.type || selectedFile.type === 'application/octet-stream') {
          const correctedType = getCorrectContentType(selectedFile.type, selectedFile.name);
          fileWithCorrectType = new File([selectedFile], selectedFile.name, {
            type: correctedType,
            lastModified: selectedFile.lastModified
          });
        }
        
        // Debug: Check what methods are available on the conversation for sending
        const conversationMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(conversation));
        const sendMethods = conversationMethods.filter(method => 
          method.toLowerCase().includes('send') || 
          method.toLowerCase().includes('message') ||
          method.toLowerCase().includes('media')
        );
        console.log('Send-related methods on conversation:', sendMethods);
        
        // Use the correct Twilio Conversations API method for sending media
        try {
          // Method 1: Send message with media using the correct Twilio API
          const sentMessage = await conversation.sendMessage({
            body: newMessage.trim() || '',
            media: fileWithCorrectType
          });
          console.log('Media message sent successfully using media property:', sentMessage);
          console.log('Sent message details:', {
            sid: sentMessage.sid,
            body: sentMessage.body,
            attachedMedia: sentMessage.attachedMedia,
            media: sentMessage.media
          });
          
        } catch (error1) {
          console.log('Media property method failed, trying alternative approaches:', error1.message);
          
          try {
            // Method 2: Try sending with media as an array
            const sentMessage = await conversation.sendMessage({
              body: newMessage.trim() || '',
              media: [fileWithCorrectType]
            });
            console.log('Media array method succeeded:', sentMessage);
            
                      } catch (error2) {
              console.log('Media array method failed, trying FormData:', error2.message);
              
              try {
                // Method 3: Try FormData with proper Twilio API
                const formData = new FormData();
                formData.append('Body', newMessage.trim() || '');
                formData.append('Media', fileWithCorrectType);
                
                const sentMessage = await conversation.sendMessage(formData);
                console.log('FormData method succeeded:', sentMessage);
                
              } catch (error3) {
                console.log('FormData method failed, trying text fallback:', error3.message);
                
                try {
                  // Method 4: Send text message as fallback
                  const fallbackMessage = newMessage.trim() || `Attempted to send ${fileWithCorrectType.type.startsWith('image/') ? 'an image' : 'a file'}: ${fileWithCorrectType.name}`;
                  const sentMessage = await conversation.sendMessage(fallbackMessage);
                  console.log('Sent fallback text message:', sentMessage);
                  
                  throw new Error(`Failed to send media file. Sent text message instead. Original errors: ${error1.message}, ${error2.message}, ${error3.message}`);
                } catch (error4) {
                  console.error('All media sending methods failed:', error4);
                  throw new Error(`Failed to send media: ${error4.message}`);
                }
              }
          }
        }
        
        // Clear file selection
        setSelectedFile(null);
        setFilePreview(null);
      } else {
        // Send text message
        console.log('Sending text message:', newMessage);
        const sentMessage = await conversation.sendMessage(newMessage);
        console.log('Text message sent successfully:', sentMessage);
      }
      
      setNewMessage("");
      
      // Auto-scroll to bottom after sending message
      setTimeout(scrollToBottom, 100);
    } catch (err) {
      console.error('Failed to send message:', err);
      console.error('Error details:', err.message, err.stack);
      setError('Failed to send message: ' + err.message);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file using helper function
    const validation = validateFile(file);
    if (!validation.valid) {
      setError(validation.error || 'Invalid file');
      return;
    }

    const correctedType = validation.correctedType || file.type;

    // Create a new File object with the corrected MIME type if needed
    let processedFile = file;
    if (correctedType !== file.type) {
      processedFile = new File([file], file.name, {
        type: correctedType,
        lastModified: file.lastModified
      });
    }

    setSelectedFile(processedFile);
    
    // Create preview for images
    if (correctedType.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setFilePreview(e.target?.result as string);
      };
      reader.readAsDataURL(processedFile);
    } else {
      setFilePreview(null);
    }

    // Clear any previous errors
    setError(null);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setFilePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  if (isLoading && isInitializing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 bg-gradient-to-br from-pink-500 to-red-500 rounded-full blur-lg opacity-50"></div>
            <div className="relative w-16 h-16 bg-white/10 backdrop-blur-xl rounded-full border border-white/20 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/70"></div>
            </div>
          </div>
          <p className="text-white/70 font-medium">Initializing chat...</p>
        </div>
      </div>
    );
  }

  // Special handling for authentication errors
  if (authError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Card className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl max-w-md mx-4">
          <CardContent className="p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-red-500/20 rounded-full flex items-center justify-center">
              <User className="w-8 h-8 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Authentication Required</h3>
            <p className="text-red-400 text-sm mb-6">{authError}</p>
            <div className="space-y-3">
              <Button
                onClick={() => navigate('/login')}
                className="w-full bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600 text-white"
              >
                Login Again
              </Button>
              <Button
                onClick={() => navigate('/dashboard')}
                variant="outline"
                className="w-full text-white/80 hover:text-white hover:bg-white/10"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Card className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl">
          <CardContent className="p-6">
            <p className="text-red-400 text-center">{error}</p>
            <Button
              onClick={() => navigate(-1)}
              variant="outline"
              className="mt-4 w-full text-white/80 hover:text-white hover:bg-white/10"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Go Back
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(139,92,246,0.1),transparent_50%)]"></div>
      
      {/* Header */}
      <div className="relative z-10 border-b border-white/10 bg-white/5 backdrop-blur-2xl sticky top-0">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
          <div className="flex items-center">
            <Button 
              onClick={() => navigate(-1)}
              variant="ghost" 
              className="text-white/80 hover:text-white hover:bg-white/10 mr-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            
            <div 
              className="flex items-center space-x-3 cursor-pointer hover:bg-white/5 rounded-lg p-2 transition-all duration-300"
              onClick={() => setShowUserProfile(true)}
            >
              <Avatar className="w-14 h-14 ring-2 ring-white/20">
                {userInfo?.profilePicture ? (
                  <AvatarImage src={userInfo.profilePicture} />
                ) : (
                  <AvatarFallback className="bg-gradient-to-r from-violet-500 to-purple-500 text-white font-bold">
                    {userInfo?.name?.charAt(0) || <User className="w-6 h-6" />}
                  </AvatarFallback>
                )}
              </Avatar>
              <div>
                <h1 className="text-lg font-semibold text-white amazon-font">
                  {userInfo?.name || 'Loading...'}
                </h1>
                {isLoadingMessages && (
                  <div className="flex items-center space-x-2 mt-1">
                    <div className="animate-spin rounded-full h-3 w-3 border-b border-white/40"></div>
                    <span className="text-xs text-white/60">Loading messages...</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* User Profile Modal */}
      <Dialog open={showUserProfile} onOpenChange={setShowUserProfile}>
        <DialogContent className="max-w-4xl bg-slate-900/95 backdrop-blur-xl border border-white/10 text-white max-h-[90vh] overflow-y-auto">
          <DialogTitle className="text-2xl font-bold text-white mb-4">{userInfo?.name || 'User Profile'}</DialogTitle>
          
          <div className="space-y-6">
            {/* User Info */}
            <div className="flex items-start gap-4">
              <Avatar className="w-20 h-20 ring-2 ring-white/20">
                {userInfo?.profilePicture ? (
                  <AvatarImage src={userInfo.profilePicture} />
                ) : (
                  <AvatarFallback className="bg-gradient-to-br from-violet-500 to-purple-500 text-white font-semibold text-xl">
                    {userInfo?.name?.charAt(0) || <User className="w-8 h-8" />}
                  </AvatarFallback>
                )}
              </Avatar>
              <div className="flex-1">
                <h2 className="text-xl font-bold text-white mb-2">{userInfo?.name}</h2>
              </div>
            </div>

            {/* Personal Insights - Questions & Answers */}
            {userQuestions && (userQuestions.Question1 || userQuestions.Question2 || userQuestions.Question3) && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-white mb-3">Personal Insights</h3>
                
                {userQuestions.Question1 && (
                  <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-medium text-white/90 mb-2">{userQuestions.Question1.Question}</h4>
                    <p className="text-white/70 text-sm leading-relaxed">{userQuestions.Question1.Answer}</p>
                  </div>
                )}
                
                {userQuestions.Question2 && (
                  <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-medium text-white/90 mb-2">{userQuestions.Question2.Question}</h4>
                    <p className="text-white/70 text-sm leading-relaxed">{userQuestions.Question2.Answer}</p>
                  </div>
                )}
                
                {userQuestions.Question3 && (
                  <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-medium text-white/90 mb-2">{userQuestions.Question3.Question}</h4>
                    <p className="text-white/70 text-sm leading-relaxed">{userQuestions.Question3.Answer}</p>
                  </div>
                )}
              </div>
            )}

            {/* Photo Carousel would go here if we had access to user's images */}
            
          </div>
          
          <div className="flex justify-end mt-6">
            <Button
              onClick={() => setShowUserProfile(false)}
              variant="outline"
              className="border-white/20 text-white/80 hover:bg-white/10"
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Chat Messages */}
      <div className="relative z-10 max-w-3xl mx-auto px-6 py-8">
        <Card 
          className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden relative"
          style={{
            backgroundImage: assets.chatBackground ? `url(${assets.chatBackground})` : undefined,
            backgroundSize: 'cover',
            backgroundPosition: 'center bottom',
            backgroundRepeat: 'no-repeat',
            backgroundAttachment: 'scroll'
          }}
        >
          {/* Background overlay for better content readability */}
          <div className="absolute inset-0 bg-black/30 backdrop-blur-[1px]"></div>
          <CardContent className="p-6 relative z-10">
            <div 
              ref={messagesContainerRef}
              className="space-y-4 h-[calc(100vh-300px)] overflow-y-auto scroll-smooth [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] relative"
            >
              {messages.map((message, index) => (
                <div
                  key={`${message.sid}-${index}-${message.timestamp.getTime()}`}
                  className={`flex relative z-10 ${message.author === localStorage.getItem('userUID') ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg p-3 ${
                      message.author === localStorage.getItem('userUID')
                        ? 'bg-blue-500/20 text-blue-100'
                        : 'bg-white/10 text-white/90'
                    }`}
                  >
                    {(() => {

                      
                      return message.media ? (
                        <div className="space-y-2">
                          {(() => {
                            const fileCategory = getFileTypeCategory(message.media.contentType);
                            const isPreviewable = isPreviewableType(message.media.contentType);
                            
                            switch (fileCategory) {
                                                             case 'image':
                                 return (
                                   <div className="relative">
                                     {message.media.url ? (
                                       <>
                                         <img 
                                           src={message.media.url} 
                                           alt={message.media.filename || 'Image'}
                                           className="max-w-full h-auto rounded-lg cursor-pointer hover:opacity-90 transition-opacity shadow-lg"
                                           style={{ maxHeight: '300px', minHeight: '100px' }}
                                           onLoad={() => {
                                             setTimeout(scrollToBottom, 100);
                                           }}
                                           onError={(e) => {
                                             e.currentTarget.style.display = 'none';
                                           }}
                                           onClick={() => window.open(message.media.url, '_blank')}
                                         />
                                         <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-sm rounded px-2 py-1">
                                           <p className="text-xs text-white/90">{message.media.filename}</p>
                                         </div>
                                       </>
                                     ) : (
                                       <div className="p-4 bg-red-500/20 rounded-lg border border-red-500/30">
                                         <ImageIcon className="w-8 h-8 text-red-300 mx-auto mb-2" />
                                         <p className="text-red-300 text-sm text-center">Image not available</p>
                                         <p className="text-xs text-red-400 mt-1 text-center">{message.media.filename}</p>
                                       </div>
                                     )}
                                   </div>
                                 );
                              
                              case 'video':
                                return (
                                  <div className="relative">
                                    {message.media.url ? (
                                      <>
                                        <video 
                                          src={message.media.url} 
                                          controls
                                          className="max-w-full h-auto rounded-lg shadow-lg"
                                          style={{ maxHeight: '300px' }}
                                                                                     onLoadedData={() => {
                                             setTimeout(scrollToBottom, 100);
                                           }}
                                          onError={(e) => {
                                            console.error('Video failed to load:', message.media.url);
                                          }}
                                        />
                                        <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur-sm rounded px-2 py-1">
                                          <p className="text-xs text-white/90">{message.media.filename}</p>
                                        </div>
                                      </>
                                    ) : (
                                      <div className="p-4 bg-red-500/20 rounded-lg border border-red-500/30">
                                        <div className="w-8 h-8 text-red-300 mx-auto mb-2">🎥</div>
                                        <p className="text-red-300 text-sm text-center">Video not available</p>
                                        <p className="text-xs text-red-400 mt-1 text-center">{message.media.filename}</p>
                                      </div>
                                    )}
                                  </div>
                                );
                              
                              case 'audio':
                                return (
                                  <div className="bg-white/10 rounded-lg p-4 border border-white/20">
                                    {message.media.url ? (
                                      <>
                                        <div className="flex items-center space-x-3 mb-3">
                                          <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
                                            <span className="text-green-400">🎵</span>
                                          </div>
                                          <div className="flex-1">
                                            <p className="text-sm text-white/90 font-medium">{message.media.filename}</p>
                                            <p className="text-xs text-white/60">
                                              {message.media.size ? `${(message.media.size / 1024 / 1024).toFixed(2)} MB` : 'Audio file'}
                                            </p>
                                          </div>
                                        </div>
                                        <audio 
                                          src={message.media.url} 
                                          controls
                                          className="w-full"
                                          onLoadedData={() => {
                                            setTimeout(scrollToBottom, 100);
                                          }}
                                          onError={(e) => {
                                            console.error('Audio failed to load:', message.media.url);
                                          }}
                                        />
                                      </>
                                    ) : (
                                      <div className="text-center">
                                        <div className="w-8 h-8 text-red-300 mx-auto mb-2">🎵</div>
                                        <p className="text-red-300 text-sm">Audio not available</p>
                                        <p className="text-xs text-red-400 mt-1">{message.media.filename}</p>
                                      </div>
                                    )}
                                  </div>
                                );
                              
                              case 'document':
                                return (
                                  <div className="bg-white/10 rounded-lg p-4 border border-white/20 hover:bg-white/15 transition-colors cursor-pointer"
                                    onClick={() => message.media.url && window.open(message.media.url, '_blank')}
                                  >
                                    <div className="flex items-center space-x-3">
                                      <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                                        {message.media.contentType.includes('pdf') ? (
                                          <span className="text-blue-400">📄</span>
                                        ) : message.media.contentType.includes('word') ? (
                                          <span className="text-blue-400">📝</span>
                                        ) : message.media.contentType.includes('excel') ? (
                                          <span className="text-green-400">📊</span>
                                        ) : message.media.contentType.includes('powerpoint') ? (
                                          <span className="text-orange-400">📽️</span>
                                        ) : (
                                          <span className="text-blue-400">📄</span>
                                        )}
                                      </div>
                                      <div className="flex-1">
                                        <p className="text-sm text-white/90 font-medium">{message.media.filename}</p>
                                        <p className="text-xs text-white/60">
                                          {message.media.size ? `${(message.media.size / 1024 / 1024).toFixed(2)} MB` : 'Document'}
                                        </p>
                                        <p className="text-xs text-blue-400">
                                          {message.media.url ? 'Click to open' : 'Not available'}
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                );
                              
                              case 'archive':
                                return (
                                  <div className="bg-white/10 rounded-lg p-4 border border-white/20">
                                    <div className="flex items-center space-x-3">
                                      <div className="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                                        <span className="text-purple-400">🗜️</span>
                                      </div>
                                      <div className="flex-1">
                                        <p className="text-sm text-white/90 font-medium">{message.media.filename}</p>
                                        <p className="text-xs text-white/60">
                                          {message.media.size ? `${(message.media.size / 1024 / 1024).toFixed(2)} MB` : 'Archive'}
                                        </p>
                                        <p className="text-xs text-purple-400">
                                          {message.media.url ? (
                                            <a href={message.media.url} download className="hover:underline">
                                              Click to download
                                            </a>
                                          ) : 'Not available'}
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                );
                              
                              case 'code':
                                return (
                                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-600/30">
                                    <div className="flex items-center space-x-3">
                                      <div className="w-10 h-10 bg-slate-600/30 rounded-lg flex items-center justify-center">
                                        <span className="text-slate-300">💻</span>
                                      </div>
                                      <div className="flex-1">
                                        <p className="text-sm text-white/90 font-medium font-mono">{message.media.filename}</p>
                                        <p className="text-xs text-white/60">
                                          {message.media.size ? `${(message.media.size / 1024).toFixed(1)} KB` : 'Code file'}
                                        </p>
                                        <p className="text-xs text-slate-400">
                                          {message.media.url ? (
                                            <a href={message.media.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                                              View code
                                            </a>
                                          ) : 'Not available'}
                                        </p>
                                      </div>
                                    </div>
                                  </div>
                                );
                              
                                                             default:
                                 return (
                                   <div className="bg-white/10 rounded-lg p-4 border border-white/20">
                                     <div className="flex items-center space-x-3">
                                       <div className="w-10 h-10 bg-gray-500/20 rounded-lg flex items-center justify-center">
                                         <Paperclip className="w-5 h-5 text-gray-400" />
                                       </div>
                                       <div className="flex-1">
                                         <p className="text-sm text-white/90 font-medium">{message.media.filename || 'Attachment'}</p>
                                         <p className="text-xs text-white/60">
                                           {message.media.size ? `${(message.media.size / 1024 / 1024).toFixed(2)} MB` : 'File'}
                                         </p>
                                         <p className="text-xs text-white/60">
                                           Type: {message.media.contentType || 'Unknown'}
                                         </p>
                                         <p className="text-xs text-gray-400">
                                           {message.media.url ? (
                                             <a href={message.media.url} download className="hover:underline">
                                               Download file
                                             </a>
                                           ) : 'Not available'}
                                         </p>
                                       </div>
                                     </div>
                                   </div>
                                 );
                            }
                          })()}
                          {message.body && message.body.trim() && <p className="text-sm mt-2">{message.body}</p>}
                        </div>
                      ) : (
                        message.body && message.body.trim() && <p className="text-sm">{message.body}</p>
                      );
                    })()}
                    <p className="text-xs mt-1 opacity-60">
                      {(() => {
                        try {
                          const date = message.timestamp instanceof Date ? message.timestamp : new Date(message.timestamp);
                          if (isNaN(date.getTime())) {
                            return 'Just now';
                          }
                          return date.toLocaleTimeString([], { 
                            hour: '2-digit', 
                            minute: '2-digit',
                            hour12: true 
                          });
                        } catch (error) {
                          return 'Just now';
                        }
                      })()}
                    </p>
                  </div>
                </div>
              ))}
              {/* Invisible element to scroll to */}
              <div ref={messagesEndRef} className="relative z-10" />
            </div>

            {/* File Preview */}
            {selectedFile && (
              <div className="mb-4 p-3 bg-white/5 rounded-lg border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white/80">Selected file:</span>
                  <Button
                    onClick={handleRemoveFile}
                    variant="ghost"
                    size="sm"
                    className="text-white/60 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex items-center space-x-3">
                  {filePreview ? (
                    <img 
                      src={filePreview} 
                      alt="Preview" 
                      className="w-16 h-16 object-cover rounded"
                    />
                  ) : (
                    <div className="w-16 h-16 bg-white/10 rounded flex items-center justify-center">
                      <ImageIcon className="w-6 h-6 text-white/60" />
                    </div>
                  )}
                  <div>
                    <p className="text-sm text-white/90">{selectedFile.name}</p>
                    <p className="text-xs text-white/60">
                      {formatFileSize(selectedFile.size)} • {getFileTypeCategory(selectedFile.type)}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Message Input */}
            <div className="mt-4 flex gap-2 items-center">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                onClick={handleAttachClick}
                variant="outline"
                size="sm"
                disabled={isBlocked}
                className={`border-white/10 flex-shrink-0 w-10 h-10 p-0 ${
                  isBlocked 
                    ? "bg-gray-500/20 text-gray-400 cursor-not-allowed" 
                    : "bg-white/5 text-white/80 hover:bg-white/10 hover:text-white"
                }`}
                title={isBlocked ? "This user has been blocked" : "Attach file"}
              >
                <Paperclip className="w-4 h-4" />
              </Button>
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={isBlocked ? "This user has been blocked" : "Type a message..."}
                disabled={isBlocked}
                className={`flex-1 min-w-0 border border-white/10 rounded-lg px-3 py-2 text-sm ${
                  isBlocked 
                    ? "bg-gray-500/20 text-gray-400 placeholder:text-gray-500 cursor-not-allowed" 
                    : "bg-white/5 text-white/90 placeholder:text-white/40 focus:outline-none focus:border-blue-500/50"
                }`}
              />
              <Button
                onClick={handleSendMessage}
                variant="outline"
                size="sm"
                disabled={isSending || isBlocked}
                className={`flex-shrink-0 w-10 h-10 p-0 ${
                  isBlocked 
                    ? "bg-red-500/20 text-red-100 hover:bg-red-500/30 cursor-not-allowed" 
                    : "bg-blue-500/20 text-blue-100 hover:bg-blue-500/30 hover:text-blue-100"
                }`}
                title={isBlocked ? "This user has been blocked" : "Send message"}
              >
                {isSending ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-100"></div>
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Chat; 