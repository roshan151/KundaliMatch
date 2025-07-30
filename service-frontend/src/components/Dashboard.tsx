import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Heart, Bell, Clock, Users, User, LogOut, Star, X, MapPin, MessageCircle, Sparkles } from "lucide-react";
import { config } from "../config/api";
import { S3_CONFIG } from "../config/s3";
import UserActions from "./UserActions";
import ProfileView from "./ProfileView";
import { formatDistanceToNow } from "date-fns";
import { motion, AnimatePresence } from "framer-motion";
import ChatWithDestiny from "./ChatWithDestiny";
import React from "react";
import { User as UserType, Notification } from "../types";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel";
import { getImageUrl, extractS3Key } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { useS3Assets } from "../hooks/useS3Assets";
import { useChatContext } from "../contexts/ChatContext";
import { useProfileContext } from "../contexts/ProfileContext";

interface DashboardMessage {
  id: string;
  text: string;
  timestamp: Date;
  userName?: string;
}

interface DashboardProps {
  userUID: string | null;
  setIsLoggedIn: (value: boolean) => void;
  onLogout: () => void;
  notifications?: Notification[];
}

interface RecommendationCard {
  recommendation_uid: string;
  name: string;
  score: number;
  chat_enabled: boolean;
  user_align: boolean;
  images?: string[]; // Array of S3 image URLs
  city?: string;
  country?: string;
  hobbies?: string;
  profession?: string;
  blocked_by_match?: boolean;
  blocked_by_user?: boolean;
  reason?: string;
  filtered?: boolean; // Flag to track if card was filtered
  MBTI?: string; // Personality type code
  MBTI_DESCRIPTION?: string; // Personality description
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

const Dashboard = ({ userUID, setIsLoggedIn, onLogout, notifications = [] }: DashboardProps) => {
  const navigate = useNavigate();
  const { assets } = useS3Assets();
  const {
    unifiedChatMessages,
    setUnifiedChatMessages,
    unifiedChatHistory,
    setUnifiedChatHistory,
    hasUserSentMessage,
    setHasUserSentMessage,
    chatHistoryRef,
    clearChatHistory,
    initializeUserSession,
    switchUser,
    addSessionSeparator
  } = useChatContext();
  
  const { refreshProfile } = useProfileContext();
  
  const [matches, setMatches] = useState<RecommendationCard[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationCard[]>([]);
  const [awaiting, setAwaiting] = useState<RecommendationCard[]>([]);
  const [messages, setMessages] = useState<DashboardMessage[]>([]);
  const [isLoading, setIsLoading] = useState<{ [key: string]: boolean }>({
    recommendations: false,
    matches: false,
    awaiting: false
  });
  const [selectedUser, setSelectedUser] = useState<RecommendationCard | null>(null);
  const [isMatchesOpen, setIsMatchesOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [systemNotifications, setSystemNotifications] = useState<Notification[]>([]);
  const [hasNewNotifications, setHasNewNotifications] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showChatWindow, setShowChatWindow] = useState(false);
  const [activeTab, setActiveTab] = useState(() => {
    // Restore last active tab from localStorage, default to "recommendations"
    return localStorage.getItem('lastActiveTab') || "recommendations";
  });
  const [loadedTabs, setLoadedTabs] = useState<Set<string>>(new Set());
  const [chatMessage, setChatMessage] = useState("");

  // Function to update active tab and save to localStorage
  const updateActiveTab = (newTab: string) => {
    setActiveTab(newTab);
    localStorage.setItem('lastActiveTab', newTab);
  };
  
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [isWaitingForUser, setIsWaitingForUser] = useState(false);
  const [isInitialResponse, setIsInitialResponse] = useState(false);
  const [isPreferenceChat, setIsPreferenceChat] = useState(false);
  const [hasUsedChatWithDestiny, setHasUsedChatWithDestiny] = useState(() => {
    // Check if user has used ChatWithDestiny in this session
    return sessionStorage.getItem(`destinyWindowChatUsed_${userUID}`) === 'true';
  });
  const [blockedUsers, setBlockedUsers] = useState<Set<string>>(new Set());

  // Fetch profile data for a recommendation card
  const fetchProfileData = async (uid: string) => {
    try {
      console.log(`Fetching profile data for UID: ${uid}`);
      const response = await fetch(`${config.URL}/get:profile/${uid}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch profile for ${uid}`);
      }

      const data = await response.json();
      console.log(`Received profile data for ${uid}:`, data);

              // Generate backend proxy URLs for all images
        if (data.IMAGES || data.images) {
          const images = data.IMAGES || data.images;
          const proxyUrls = images.map((url: string) => {
            return getImageUrl(url); // Use backend proxy for secure image access
          });
          data.IMAGES = proxyUrls;
          data.images = proxyUrls;
        }

      return data;
    } catch (error) {
      console.error(`Error fetching profile for ${uid}:`, error);
      return null;
    }
  };

  // Helper function to process recommendations from cache (filter removal)
  const processRecommendationsFromCache = async (recommendationCards: any[]) => {
    console.log('Processing recommendations from cache:', recommendationCards);
    
    if (recommendationCards && Array.isArray(recommendationCards) && recommendationCards.length > 0) {
      try {
        // Fetch profile data for each recommendation
        const enrichedRecommendations = await Promise.all(
          recommendationCards.map(async (rec: any) => {
            const uid = rec.recommendation_uid;
            if (!uid) {
              console.error('No UID found in recommendation:', rec);
              return rec;
            }
            
            const profileData = await fetchProfileData(uid);
            if (profileData) {
              return {
                ...rec,
                recommendation_uid: uid,
                name: profileData.NAME || profileData.name || rec.name,
                images: profileData.IMAGES || profileData.images || [],
                city: profileData.CITY || profileData.city,
                country: profileData.COUNTRY || profileData.country,
                profession: profileData.PROFESSION || profileData.profession,
                hobbies: profileData.HOBBIES || profileData.hobbies,
                gender: profileData.GENDER || profileData.gender,
                dob: profileData.DOB || profileData.dob,
                blocked_by_match: rec.blocked_by_match || false,
                blocked_by_user: rec.blocked_by_user || false,
                reason: rec.reason,
                MBTI: rec.MBTI || profileData.MBTI,
                MBTI_DESCRIPTION: rec.MBTI_DESCRIPTION || profileData.MBTI_DESCRIPTION
              };
            }
            return rec;
          })
        );
        
        console.log('Enriched recommendations from cache:', enrichedRecommendations);
        
        // Update the recommendations state
        setRecommendations(enrichedRecommendations);
        
        // Switch to recommendations tab if not already there
        if (activeTab !== 'recommendations') {
          console.log('Switching to recommendations tab');
          updateActiveTab('recommendations');
        }
        
        // Mark recommendations tab as loaded
        setLoadedTabs(prev => new Set([...prev, 'recommendations']));
        
        console.log('Successfully updated recommendations from cache');
      } catch (error) {
        console.error('Error processing recommendations from cache:', error);
      }
    } else {
      console.log('No valid recommendations found in cache');
    }
  };

  // Helper function to process recommendations from chat API response
  // Handles responses from chat:user, chat:app, and chat:preference endpoints
  // Key features:
  // 1. Checks for filter_applied=true and refreshes recommendations queue accordingly
  // 2. Sets filtered=false for all processed recommendations to reset filter state
  // 3. Supports both new filter-based processing and legacy recommendation processing
  const processRecommendationsFromChat = async (data: any) => {
    console.log('Checking for recommendations in chat response:', data);
    
    // Check if filter_applied is true before processing recommendations
    // This applies to both chat:user and chat:preference responses
    if (data.filter_applied === true) {
      console.log('Filter applied detected (from chat:user or chat:preference), filtering recommendations to ONLY show provided cards');
      
      if (data.recommendations && Array.isArray(data.recommendations) && data.recommendations.length > 0) {
        console.log(`Found ${data.recommendations.length} filtered recommendations - REPLACING entire recommendations list:`, data.recommendations);
        
        try {
          // Fetch profile data for each filtered recommendation
          const enrichedRecommendations = await Promise.all(
            data.recommendations.map(async (rec: any) => {
              // Handle both UID formats from backend
              const uid = rec.UID || rec.recommendation_uid;
              console.log('Processing recommendation:', rec, 'extracted UID:', uid);
              
              if (!uid) {
                console.error('No UID found in recommendation (checked both UID and recommendation_uid):', rec);
                return rec;
              }
              
              const profileData = await fetchProfileData(uid);
              console.log(`Profile data for ${uid}:`, profileData);
              
              if (profileData) {
                const enrichedCard = {
                  ...rec,
                  recommendation_uid: uid, // Standardize field name
                  UID: uid, // Keep both for compatibility
                  name: profileData.NAME || profileData.name || rec.name || rec.NAME,
                  images: profileData.IMAGES || profileData.images || [],
                  city: profileData.CITY || profileData.city,
                  country: profileData.COUNTRY || profileData.country,
                  profession: profileData.PROFESSION || profileData.profession,
                  hobbies: profileData.HOBBIES || profileData.hobbies,
                  gender: profileData.GENDER || profileData.gender,
                  dob: profileData.DOB || profileData.dob,
                  blocked_by_match: rec.blocked_by_match || false,
                  blocked_by_user: rec.blocked_by_user || false,
                  reason: rec.reason || rec.USER_REASON || 'Not Present',
                  score: rec.score || rec.RECOMMENDATION_SCORE || 0,
                  chat_enabled: rec.chat_enabled || false,
                  user_align: rec.user_align || false,
                  Question1: rec.Question1 || {},
                  Question2: rec.Question2 || {},
                  Question3: rec.Question3 || {},
                  MBTI: rec.MBTI || profileData.MBTI,
                  MBTI_DESCRIPTION: rec.MBTI_DESCRIPTION || profileData.MBTI_DESCRIPTION,
                  filtered: false // Set filtered to false for recommendations from filter refresh
                };
                console.log('Created enriched card:', enrichedCard);
                return enrichedCard;
              } else {
                console.error(`Failed to fetch profile data for UID: ${uid}`);
                return {
                  ...rec,
                  recommendation_uid: uid,
                  UID: uid,
                  name: rec.name || rec.NAME || 'Unknown User',
                  images: [],
                  reason: rec.reason || rec.USER_REASON || 'Not Present',
                  filtered: false
                };
              }
            })
          );
          
          console.log('Enriched filtered recommendations (ONLY these will be shown):', enrichedRecommendations);
          
          // REPLACE the entire recommendations state with ONLY the filtered cards
          // This ensures only the cards from chat:user response are displayed
          setRecommendations(enrichedRecommendations);
          
          // Switch to recommendations tab if not already there to show filtered results
          if (activeTab !== 'recommendations') {
            console.log('Switching to recommendations tab to show filtered results');
            updateActiveTab('recommendations');
          }
          
          // Mark recommendations tab as loaded
          setLoadedTabs(prev => new Set([...prev, 'recommendations']));
          
          // Refresh user profile to reflect new filters
          if (userUID) {
            console.log('Refreshing user profile due to filter_applied=true');
            try {
              await refreshProfile(userUID);
              console.log('Profile refresh triggered successfully');
            } catch (error) {
              console.error('Error refreshing profile after filter applied:', error);
            }
          }
          
          console.log(`Successfully applied filter - now showing ONLY ${enrichedRecommendations.length} filtered recommendations`);
        } catch (error) {
          console.error('Error processing filtered recommendations:', error);
        }
      } else if (data.recommendations && Array.isArray(data.recommendations) && data.recommendations.length === 0) {
        console.log('Filter applied with empty recommendations array - clearing recommendations list');
        // If filter is applied but recommendations array is empty, clear the recommendations
        setRecommendations([]);
        
        // Switch to recommendations tab to show empty filtered results
        if (activeTab !== 'recommendations') {
          console.log('Switching to recommendations tab to show empty filtered results');
          updateActiveTab('recommendations');
        }
        
        setLoadedTabs(prev => new Set([...prev, 'recommendations']));
        console.log('Successfully applied filter - no matching recommendations found');
      } else {
        console.log('Filter applied but no valid recommendations array found in response');
      }
    } else if (data.recommendations && Array.isArray(data.recommendations)) {
      console.log(`Found recommendations array with ${data.recommendations.length} items (legacy processing):`, data.recommendations);
      
      if (data.recommendations.length > 1) {
        console.log('Processing recommendations from chat response (more than 1 item):', data.recommendations);
        
        try {
          // Fetch profile data for each recommendation
          const enrichedRecommendations = await Promise.all(
            data.recommendations.map(async (rec: any) => {
              const uid = rec.recommendation_uid;
              if (!uid) {
                console.error('No UID found in recommendation:', rec);
                return rec;
              }
              
              const profileData = await fetchProfileData(uid);
              if (profileData) {
                return {
                  ...rec,
                  recommendation_uid: uid,
                  name: profileData.NAME || profileData.name || rec.name,
                  images: profileData.IMAGES || profileData.images || [],
                  city: profileData.CITY || profileData.city,
                  country: profileData.COUNTRY || profileData.country,
                  profession: profileData.PROFESSION || profileData.profession,
                  hobbies: profileData.HOBBIES || profileData.hobbies,
                  gender: profileData.GENDER || profileData.gender,
                  dob: profileData.DOB || profileData.dob,
                  blocked_by_match: rec.blocked_by_match || false,
                  blocked_by_user: rec.blocked_by_user || false,
                  reason: rec.reason,
                  filtered: false // Set filtered to false for legacy recommendations processing
                };
              }
              return rec;
            })
          );
          
          console.log('Enriched recommendations:', enrichedRecommendations);
          
          // Update the recommendations state
          setRecommendations(enrichedRecommendations);
          
          // Switch to recommendations tab if not already there
          if (activeTab !== 'recommendations') {
            console.log('Switching to recommendations tab');
            updateActiveTab('recommendations');
          }
          
          // Mark recommendations tab as loaded
          setLoadedTabs(prev => new Set([...prev, 'recommendations']));
          
          console.log('Successfully updated recommendations from chat response');
        } catch (error) {
          console.error('Error processing recommendations from chat response:', error);
        }
      } else {
        console.log('Recommendations array has only', data.recommendations.length, 'item(s), need more than 1 to update');
      }
    } else {
      console.log('No filter_applied=true or recommendations key found in response');
    }
  };

  // Fetch data for each tab
  const fetchTabData = async (tab: string) => {
    if (!userUID) return;
    
    // If tab is already loaded and has data, don't fetch again
    if (loadedTabs.has(tab)) {
      const hasData = tab === "recommendations" ? recommendations.length > 0 :
                     tab === "matches" ? matches.length > 0 :
                     awaiting.length > 0;
      if (hasData) return;
    }
    
    try {
      setIsLoading(prev => ({ ...prev, [tab]: true }));
      const endpoint = tab === "recommendations" 
        ? `/get:recommendations/${userUID}`
        : tab === "matches"
        ? `/get:matches/${userUID}`
        : `/get:awaiting/${userUID}`;

      console.log(`Fetching ${tab} data from: ${config.URL}${endpoint}`);

      const response = await fetch(`${config.URL}${endpoint}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch ${tab}`);
      }

      const data = await response.json();
      console.log(`Raw ${tab} data:`, data);
      
      // Get the list of cards from the response
      const cards = data.cards || [];
      console.log(`Cards from ${tab}:`, cards);
      
      if (cards.length === 0) {
        console.log(`No cards found for ${tab}`);
        switch (tab) {
          case "recommendations":
            setRecommendations([]);
            break;
          case "matches":
            setMatches([]);
            break;
          case "awaiting":
            setAwaiting([]);
            break;
        }
        setLoadedTabs(prev => new Set([...prev, tab]));
        return;
      }

      // Fetch profile data for each card
      const enrichedCards = await Promise.all(
        cards.map(async (card: any) => {
          console.log(`Processing card:`, card);
          const uid = card.recommendation_uid;
          if (!uid) {
            console.error('No UID found in card:', card);
            return card;
          }
          console.log(`Fetching profile for UID: ${uid}`);
          const profileData = await fetchProfileData(uid);
          if (profileData) {
            // Check if card has filtered property set to true and reset it to false
            // This ensures filtered cards are properly reset when loading/refreshing recommendations
            const isFiltered = card.filtered === true;
            if (isFiltered) {
              console.log(`Card ${uid} has filtered=true, resetting to false for queue: ${tab}`);
            }
            
            const enrichedCard = {
              ...card,
              recommendation_uid: uid,
              name: profileData.NAME || profileData.name || card.name,
              images: profileData.IMAGES || profileData.images || [],
              city: profileData.CITY || profileData.city,
              country: profileData.COUNTRY || profileData.country,
              profession: profileData.PROFESSION || profileData.profession,
              hobbies: profileData.HOBBIES || profileData.hobbies,
              gender: profileData.GENDER || profileData.gender,
              dob: profileData.DOB || profileData.dob,
              blocked_by_match: card.blocked_by_match || false,
              blocked_by_user: card.blocked_by_user || false,
              reason: card.reason, // Preserve the reason field from the backend
              Question1: card.Question1,
              Question2: card.Question2,
              Question3: card.Question3,
              MBTI: card.MBTI || profileData.MBTI,
              MBTI_DESCRIPTION: card.MBTI_DESCRIPTION || profileData.MBTI_DESCRIPTION,
              filtered: false // Always set filtered to false when processing cards
            };
            console.log(`Created enriched card:`, enrichedCard);
            return enrichedCard;
          }
          console.log(`No profile data found for ${uid}, returning original card`);
          return card;
        })
      );
      
      console.log(`Final enriched ${tab} data:`, enrichedCards);
      
      switch (tab) {
        case "recommendations":
          setRecommendations(enrichedCards);
          break;
        case "matches":
          setMatches(enrichedCards);
          break;
        case "awaiting":
          setAwaiting(enrichedCards);
          break;
      }
      setLoadedTabs(prev => new Set([...prev, tab]));
    } catch (error) {
      console.error(`Error fetching ${tab}:`, error);
    } finally {
      setIsLoading(prev => ({ ...prev, [tab]: false }));
    }
  };

  // Effect to fetch initial data and check for updated recommendations cache
  useEffect(() => {
    if (userUID) {
      // Check if there are updated recommendations from profile filter removal
      const updatedRecommendations = localStorage.getItem('updatedRecommendations');
      const cacheTimestamp = localStorage.getItem('recommendationsCacheTimestamp');
      
      if (updatedRecommendations && cacheTimestamp) {
        try {
          const parsedRecommendations = JSON.parse(updatedRecommendations);
          console.log('Found updated recommendations from filter removal:', parsedRecommendations);
          
          // Process the updated recommendations
          processRecommendationsFromCache(parsedRecommendations);
          
          // Clean up the cache
          localStorage.removeItem('updatedRecommendations');
          localStorage.removeItem('recommendationsCacheTimestamp');
          
          return; // Don't fetch from server if we have updated cache
        } catch (error) {
          console.error('Error parsing updated recommendations:', error);
        }
      }
      
      console.log('Initial data fetch for recommendations...');
      fetchTabData('recommendations');
    }
  }, [userUID]);

  // Effect to handle tab changes
  useEffect(() => {
    if (userUID) {
      console.log(`Tab changed to ${activeTab}, fetching data if needed...`);
      fetchTabData(activeTab);
    }
  }, [userUID, activeTab]);

  // Effect to initialize user session when userUID changes
  useEffect(() => {
    if (userUID) {
      console.log('Initializing chat session for user:', userUID);
      initializeUserSession(userUID);
      
      // Reset ChatWithDestiny usage tracking for new user session
      const hasUsedInSession = sessionStorage.getItem(`destinyWindowChatUsed_${userUID}`) === 'true';
      setHasUsedChatWithDestiny(hasUsedInSession);
    }
  }, [userUID, initializeUserSession]);

  // Effect to handle notifications
  useEffect(() => {
    if (notifications && notifications.length > 0) {
      console.log('Setting system notifications from props:', notifications);
      setSystemNotifications(notifications);
      setHasNewNotifications(true);
    }
  }, [notifications]);

  // Effect to initialize chat with destiny after a delay
  useEffect(() => {
    // Check if user has dismissed or completed the chat, or already sent a message
    const hasDismissed = sessionStorage.getItem('destinyChatDismissed');
    const hasCompleted = sessionStorage.getItem('destinyChatCompleted');
    const hasUserChatted = sessionStorage.getItem('destinyUserHasChatted');
      
    // Disable delayed popup if destiny chat window is open or user is already using ChatWithDestiny
    if (!hasDismissed && !hasCompleted && !hasUserChatted && !hasUserSentMessage && !showChatWindow && !hasUsedChatWithDestiny && userUID) {
      console.log('Setting up chat timer with UID:', userUID);
      // Generate random delay between 2 and 5 minutes
      const randomDelay = Math.floor(Math.random() * (300000 - 120000) + 120000);
      console.log(`Chat will appear in ${randomDelay/1000} seconds (${Math.round(randomDelay/60000)} minutes)`);
      
      const timer = setTimeout(async () => {
        // Double-check that destiny chat window is still not open and user hasn't started using ChatWithDestiny
        if (showChatWindow || hasUsedChatWithDestiny) {
          console.log('Destiny chat window is open or user is using ChatWithDestiny, skipping delayed popup');
          return;
        }
        
        try {
          console.log('Making chat:initiate call for UID:', userUID);
          const response = await fetch(`http://localhost:8040/chat:app`, {
            method: 'POST',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'Origin': 'http://localhost:8080'
            },
            body: JSON.stringify({
              uid: userUID
            })
          });
          
          if (response.ok) {
            const data = await response.json();
            console.log('Chat initiated successfully:', data);
            setChatMessage(data.message);
            
            // Process recommendations if present
            await processRecommendationsFromChat(data);
            
            // Add separator for chat:app messages
            addSessionSeparator('chat-type');
            
            // Initialize unified chat state with the first message
            const initialMessage = { 
              text: data.message, 
              isUser: false, 
              timestamp: new Date(),
              type: 'chat:app' as const
            };
            setUnifiedChatMessages(prev => [...prev, initialMessage]);
            setUnifiedChatHistory([{ text: data.message, isUser: false }]);
            setShowChat(true);
            setIsInitialResponse(true);
          } else {
            console.error('Failed to initiate chat:', response.status);
          }
        } catch (error) {
          console.error('Error initiating chat:', error);
        }
      }, randomDelay);
      
      return () => clearTimeout(timer);
    } else if (showChatWindow) {
      console.log('Destiny chat window is open, delaying popup is disabled');
    } else if (hasUsedChatWithDestiny) {
      console.log('User is already using ChatWithDestiny for chat:user, delaying popup is disabled');
    }
  }, [userUID, showChatWindow, hasUsedChatWithDestiny]);

  const addMessage = (text: string, userName?: string) => {
    const newMessage: DashboardMessage = {
      id: Date.now().toString(),
      text,
      timestamp: new Date(),
      userName
    };
    setMessages(prev => [newMessage, ...prev]);
    setHasNewNotifications(true);
  };

  const handleNotificationsOpen = () => {
    setIsNotificationsOpen(true);
    setHasNewNotifications(false);
  };

  const handleLogout = () => {
    // Clear chat history when logging out
    clearChatHistory();
    
    if (onLogout) {
      onLogout();
    } else {
      localStorage.removeItem('userUID');
      localStorage.removeItem('userData');
      localStorage.removeItem('profileData');
      localStorage.removeItem('dashboardData');
      setIsLoggedIn(false);
    }
  };

  const handleViewProfile = () => {
    navigate("/profile");
  };

  const handleUserClick = (user: RecommendationCard) => {
    setSelectedUser(user);
  };

  const handleBackToList = () => {
    setSelectedUser(null);
  };

  const handleActionComplete = (action: 'skip' | 'align' | 'block', queue?: string, message?: string, responseData?: any) => {
    if (!selectedUser) return;

    const userUID = selectedUser.recommendation_uid;
    
    // Remove user from current list
    setRecommendations(prev => prev.filter(user => user.recommendation_uid !== userUID));
    setMatches(prev => prev.filter(user => user.recommendation_uid !== userUID));
    setAwaiting(prev => prev.filter(user => user.recommendation_uid !== userUID));

    // Add message to notifications if present
    if (message && message !== 'None') {
      addMessage(message, selectedUser.name);
    }

    // For block action, handle based on API response and don't modify queues
    if (action === 'block') {
      setBlockedUsers(prev => {
        const newSet = new Set(prev);
        // Check if API response indicates user is blocked or unblocked
        if (responseData && responseData.user_block !== undefined) {
          if (responseData.user_block === false) {
            // API says user is unblocked, remove from blocked set
            newSet.delete(userUID);
          } else if (responseData.user_block === true) {
            // API says user is blocked, add to blocked set
            newSet.add(userUID);
          }
        } else {
          // Fallback to toggle behavior if user_block not in response
          if (newSet.has(userUID)) {
            newSet.delete(userUID);
          } else {
            newSet.add(userUID);
          }
        }
        return newSet;
      });
      setSelectedUser(null);
      return;
    }

    // Handle queue management
    if (queue && queue !== 'None') {
      const updatedUser = {
        ...selectedUser,
        user_align: action === 'align'
      };

      switch (queue) {
        case 'MATCHED':
        case 'Matched':
          setMatches(prev => [...prev.filter(u => u.recommendation_uid !== userUID), updatedUser]);
          break;
        case 'AWAITING':
        case 'Awaiting':
          setAwaiting(prev => [...prev.filter(u => u.recommendation_uid !== userUID), updatedUser]);
          break;
      }
    }

    setSelectedUser(null);
  };

  const formatNotificationDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return dateStr;
    }
  };

  // Count only new notifications for the badge
  const newNotificationCount = systemNotifications.filter(notification => notification.isNew === true).length;
  const totalNotificationCount = messages.length + newNotificationCount;

  const UserCard = React.forwardRef<HTMLDivElement, { user: RecommendationCard; queue?: string }>(({ user, queue }, ref) => {
    const [isLoading, setIsLoading] = useState(false);
    const [showPhotos, setShowPhotos] = useState(false);
    const [profileImage, setProfileImage] = useState<string | null>(null);

    // Set profile image when user data changes
    useEffect(() => {
      if (user.images && user.images.length > 0) {
        setProfileImage(user.images[0]); // Use the first image URL directly
      }
    }, [user.images]);

    const handleCardClick = (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).closest('button')) return;
      setShowPhotos(true);
    };

    const handleAction = async (actionType: 'skip' | 'align' | 'block') => {
      if (!userUID) return;
      
      setIsLoading(true);
      try {
        const metadata = {
          uid: userUID,
          action: actionType,
          recommendation_uid: user.recommendation_uid
        };

        const response = await fetch(`${config.URL}/account:action`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(metadata)
        });

        if (response.ok) {
          const data = await response.json();
          
          if (data.error === 'OK') {
            const queue = data.queue;
            const message = data.message;

            if (message && message !== 'None') {
              addMessage(message, user.name);
            }

            // For block action, handle based on API response
            if (actionType === 'block') {
              setBlockedUsers(prev => {
                const newSet = new Set(prev);
                // Check if API response indicates user is blocked or unblocked
                if (data.user_block === false) {
                  // API says user is unblocked, remove from blocked set
                  newSet.delete(user.recommendation_uid);
                } else if (data.user_block === true) {
                  // API says user is blocked, add to blocked set
                  newSet.add(user.recommendation_uid);
                } else {
                  // Fallback to toggle behavior if user_block not in response
                  if (newSet.has(user.recommendation_uid)) {
                    newSet.delete(user.recommendation_uid);
                  } else {
                    newSet.add(user.recommendation_uid);
                  }
                }
                return newSet;
              });
              return;
            }

            // Remove user from all queues first (for skip and align actions)
            setRecommendations(prev => prev.filter(u => u.recommendation_uid !== user.recommendation_uid));
            setMatches(prev => prev.filter(u => u.recommendation_uid !== user.recommendation_uid));
            setAwaiting(prev => prev.filter(u => u.recommendation_uid !== user.recommendation_uid));

            // If action is skip, we don't need to add to any queue
            if (actionType === 'skip') {
              return;
            }

            // Only add to new queue if it's an align action and we have a queue
            if (queue && queue !== 'None') {
              const updatedUser = {
                ...user,
                user_align: actionType === 'align'
              };

              switch (queue) {
                case 'MATCHED':
                case 'Matched':
                  setMatches(prev => [...prev, updatedUser]);
                  break;
                case 'AWAITING':
                case 'Awaiting':
                  setAwaiting(prev => [...prev, updatedUser]);
                  break;
              }
            }
          }
        }
      } catch (error) {
        console.error('Action error:', error);
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <>
        <motion.div
          ref={ref}
          className="cursor-pointer"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          <Card className="relative overflow-hidden border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
            <CardContent className="p-6" onClick={handleCardClick}>
              <div className="flex items-center space-x-4 mb-4">
                <Avatar className="w-16 h-16 ring-2 ring-white/20">
                  {profileImage ? (
                    <AvatarImage src={profileImage} />
                  ) : (
                    <AvatarFallback className="bg-gradient-to-r from-violet-500 to-purple-500 text-white text-xl font-bold">
                      {user.name?.charAt(0) || <User className="w-8 h-8" />}
                    </AvatarFallback>
                  )}
                </Avatar>
                <div>
                  <h3 className="text-lg font-semibold text-white">{user.name}</h3>
                  {user.score !== undefined && (
                    <div className="flex items-center mt-1">
                      <Star className="w-4 h-4 text-yellow-400 mr-1" />
                      <span className="text-sm text-white/70 font-medium">
                        Compatibility: {user.score}/10
                      </span>
                    </div>
                  )}
                  {user.city && user.country && (
                    <div className="flex items-center mt-1">
                      <MapPin className="w-4 h-4 text-white/60 mr-1" />
                      <span className="text-sm text-white/60">
                        {user.city}, {user.country}
                      </span>
                    </div>
                  )}
                  {user.hobbies && (
                    <div className="mt-1">
                      <span className="text-sm text-white/60">
                        {user.hobbies.split(',').slice(0, 2).join(', ')}
                        {user.hobbies.split(',').length > 2 ? '...' : ''}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-center items-center gap-6 mt-6">
                {queue === 'awaiting' ? (
                  // Awaiting queue logic: show align and skip buttons if user_align is false, waiting icon and skip if true
                  user.user_align ? (
                    // Show waiting icon and skip button when user has already aligned
                    <>
                      <div className="relative group">
                        <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 to-orange-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                        <div className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 text-white/80 transition-all duration-300 shadow-2xl flex items-center justify-center">
                          <Clock className="w-4 h-4 animate-pulse" />
                        </div>
                        <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                          Waiting
                        </span>
                      </div>

                      <div className="relative group">
                        <div className="absolute -inset-1 bg-gradient-to-r from-red-500 to-pink-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                        <Button
                          onClick={e => { e.stopPropagation(); handleAction('skip'); }}
                          variant="outline"
                          size="lg"
                          disabled={isLoading}
                          className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-red-400/50 text-white/80 hover:text-red-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-red-500/25 group-hover:bg-gradient-to-r group-hover:from-red-500/10 group-hover:to-pink-500/10"
                        >
                          <X className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
                        </Button>
                        <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                          Skip
                        </span>
                      </div>
                    </>
                  ) : (
                    // Show align and skip buttons when user hasn't aligned yet
                    <>
                      <div className="relative group">
                        <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-green-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                        <Button
                          onClick={e => { e.stopPropagation(); handleAction('align'); }}
                          variant="outline"
                          size="lg"
                          disabled={isLoading}
                          className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-emerald-400/50 text-white/80 hover:text-emerald-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-emerald-500/25 group-hover:bg-gradient-to-r group-hover:from-emerald-500/10 group-hover:to-green-500/10"
                        >
                          <Heart className="w-4 h-4 group-hover:scale-110 group-hover:fill-current transition-all duration-300" />
                        </Button>
                        <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                          Align
                        </span>
                      </div>

                      <div className="relative group">
                        <div className="absolute -inset-1 bg-gradient-to-r from-red-500 to-pink-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                        <Button
                          onClick={e => { e.stopPropagation(); handleAction('skip'); }}
                          variant="outline"
                          size="lg"
                          disabled={isLoading}
                          className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-red-400/50 text-white/80 hover:text-red-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-red-500/25 group-hover:bg-gradient-to-r group-hover:from-red-500/10 group-hover:to-pink-500/10"
                        >
                          <X className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
                        </Button>
                        <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                          Skip
                        </span>
                      </div>
                    </>
                  )
                ) : user.user_align ? (
                  // Show chat and block buttons for matched users (non-awaiting queues)
                  <>
                    <div className="relative group">
                      <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-green-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                      <Button
                        onClick={e => { 
                          e.stopPropagation(); 
                          const isBlockedByEither = user.blocked_by_match || user.blocked_by_user || blockedUsers.has(user.recommendation_uid);
                          navigate(`/chat/${user.recommendation_uid}`, {
                            state: {
                              userName: user.name,
                              userProfilePicture: profileImage,
                              isBlocked: isBlockedByEither,
                              Question1: user.Question1,
                              Question2: user.Question2,
                              Question3: user.Question3
                            }
                          });
                        }}
                        variant="outline"
                        size="lg"
                        className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-emerald-400/50 text-white/80 hover:text-emerald-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-emerald-500/25 group-hover:bg-gradient-to-r group-hover:from-emerald-500/10 group-hover:to-green-500/10"
                      >
                        <MessageCircle className="w-4 h-4 group-hover:scale-110 transition-all duration-300" />
                      </Button>
                      <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                        Chat
                      </span>
                    </div>

                    <div className="relative group">
                      {(() => {
                        const isBlockedByMatch = user.blocked_by_match;
                        const isBlockedByUser = user.blocked_by_user || blockedUsers.has(user.recommendation_uid);
                        const canUnblock = isBlockedByUser && !isBlockedByMatch;
                        const isBlocked = isBlockedByMatch || isBlockedByUser;
                        
                        return (
                          <>
                            <div className={`absolute -inset-1 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500 ${
                              isBlocked
                                ? canUnblock 
                                  ? "bg-gradient-to-r from-green-500 to-emerald-500" 
                                  : "bg-gradient-to-r from-gray-500 to-gray-600"
                                : "bg-gradient-to-r from-red-500 to-pink-500"
                            }`}></div>
                            <Button
                              onClick={e => { 
                                e.stopPropagation(); 
                                if (!isBlockedByMatch) {
                                  handleAction('block');
                                }
                              }}
                              variant="outline"
                              size="lg"
                              disabled={isLoading || isBlockedByMatch}
                              className={`relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 transition-all duration-300 shadow-2xl ${
                                isBlockedByMatch
                                  ? "cursor-not-allowed text-gray-400 border-gray-500/50"
                                  : isBlockedByUser
                                    ? "hover:scale-110 hover:border-green-400/50 text-white/80 hover:text-green-300 hover:shadow-green-500/25 group-hover:bg-gradient-to-r group-hover:from-green-500/10 group-hover:to-emerald-500/10"
                                    : "hover:scale-110 hover:border-red-400/50 text-white/80 hover:text-red-300 hover:shadow-red-500/25 group-hover:bg-gradient-to-r group-hover:from-red-500/10 group-hover:to-pink-500/10"
                              }`}
                              title={
                                isBlockedByMatch 
                                  ? "This user has blocked you - cannot unblock" 
                                  : isBlockedByUser 
                                    ? "Click to unblock this user" 
                                    : "Click to block this user"
                              }
                            >
                              <X className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
                            </Button>
                            <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                              {isBlockedByMatch ? "Blocked" : isBlockedByUser ? "Unblock" : "Block"}
                            </span>
                          </>
                        );
                      })()}
                    </div>
                  </>
                ) : (
                  // Show align and skip buttons for non-matched users
                  <>
                    <div className="relative group">
                      <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-green-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                      <Button
                        onClick={e => { e.stopPropagation(); handleAction('align'); }}
                        variant="outline"
                        size="lg"
                        disabled={isLoading}
                        className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-emerald-400/50 text-white/80 hover:text-emerald-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-emerald-500/25 group-hover:bg-gradient-to-r group-hover:from-emerald-500/10 group-hover:to-green-500/10"
                      >
                        <Heart className="w-4 h-4 group-hover:scale-110 group-hover:fill-current transition-all duration-300" />
                      </Button>
                      <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                        Align
                      </span>
                    </div>

                    <div className="relative group">
                      <div className="absolute -inset-1 bg-gradient-to-r from-red-500 to-pink-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                      <Button
                        onClick={e => { e.stopPropagation(); handleAction('skip'); }}
                        variant="outline"
                        size="lg"
                        disabled={isLoading}
                        className="relative w-12 h-12 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-red-400/50 text-white/80 hover:text-red-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-red-500/25 group-hover:bg-gradient-to-r group-hover:from-red-500/10 group-hover:to-pink-500/10"
                      >
                        <X className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
                      </Button>
                      <span className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-white/60 font-medium">
                        Skip
                      </span>
                    </div>
                  </>
                )}
              </div>
              
              {user.reason && (
                <>
                  <div className="mt-8 mx-8">
                    <hr className="border-white/30 border-t-2" />
                  </div>
                  <div className="mt-4 text-center">
                    <p className="text-sm text-white/70 italic">
                      "{user.reason}"
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <Dialog open={showPhotos} onOpenChange={setShowPhotos}>
          <DialogContent 
            className="max-w-lg max-h-[90vh] bg-white/5 backdrop-blur-xl border border-white/10 [&>button]:hidden overflow-hidden p-0"
            style={{
              backgroundImage: assets.contentBackground ? `url(${assets.contentBackground})` : undefined,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              backgroundRepeat: 'no-repeat'
            }}
          >
            {/* Background overlay for better content readability */}
            <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"></div>
            
            <DialogTitle className="sr-only">User Profile Photos</DialogTitle>
            <DialogDescription className="sr-only">
              View and browse through user's profile photos
            </DialogDescription>
            <div className="absolute right-4 top-4 z-50">
              <div className="relative group p-1">
                <div className="absolute -inset-2 bg-gradient-to-r from-red-500 to-pink-500 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500 pointer-events-none"></div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative h-10 w-10 rounded-full bg-white/5 backdrop-blur-xl border-2 border-white/10 hover:border-red-400/50 text-white/80 hover:text-red-300 transition-all duration-300 hover:scale-110 shadow-2xl hover:shadow-red-500/25 group-hover:bg-gradient-to-r group-hover:from-red-500/10 group-hover:to-pink-500/10 cursor-pointer"
                  onClick={() => setShowPhotos(false)}
                >
                  <X className="h-5 w-5 group-hover:rotate-90 transition-transform duration-300" />
                  <span className="sr-only">Close</span>
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-6 pt-4 pb-6 px-6 relative z-10 max-h-[calc(90vh-2rem)] overflow-y-auto scrollbar-hide [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
              <div className="flex items-start gap-4">
                <Avatar className="w-20 h-20 ring-2 ring-white/20">
                  {profileImage ? (
                    <AvatarImage src={profileImage} />
                  ) : (
                    <AvatarFallback className="bg-gradient-to-br from-violet-500 to-purple-500 text-white font-semibold text-xl">
                      {user.name?.charAt(0) || <User className="w-8 h-8" />}
                    </AvatarFallback>
                  )}
                </Avatar>
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-white mb-2">{user.name}</h2>
                  {user.score !== undefined && (
                    <p className="text-white/80 flex items-center gap-2 mb-2 text-sm">
                      <Star className="w-4 h-4 text-yellow-400" />
                      Compatibility: {user.score}/10
                    </p>
                  )}
                  {user.MBTI && (
                    <p className="text-white/80 flex items-center gap-2 mb-2 text-sm">
                      <Sparkles className="w-4 h-4 text-purple-400" />
                      Personality Type: <span className="font-semibold text-purple-300">{user.MBTI}</span>
                    </p>
                  )}
                  {user.city && user.country && (
                    <p className="text-white/80 flex items-center gap-2 mb-2 text-sm">
                      <MapPin className="w-4 h-4" />
                      {user.city}, {user.country}
                    </p>
                  )}
                  {user.hobbies && (
                    <div className="mb-2">
                      <p className="text-white/80 text-sm font-medium mb-1">Hobbies</p>
                      <div className="flex flex-wrap gap-2">
                        {user.hobbies.split(',').map((hobby, index) => (
                          <Badge 
                            key={index}
                            variant="secondary" 
                            className="bg-white/10 text-white/80 border-white/20"
                          >
                            {hobby.trim()}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {user.images && user.images.length > 0 && (
                <Carousel className="w-full max-w-md mx-auto px-12">
                  <CarouselContent className="flex items-center">
                    {user.images.map((image, index) => (
                      <CarouselItem key={index} className="flex items-center justify-center">
                        <div className="relative aspect-square rounded-xl overflow-hidden max-h-[300px] w-full">
                          <img
                            src={image}
                            alt={`${user.name}'s photo ${index + 1}`}
                            className="object-cover w-full h-full"
                          />
                        </div>
                      </CarouselItem>
                    ))}
                  </CarouselContent>
                  <CarouselPrevious className="absolute left-0 top-1/2 -translate-y-1/2 bg-white/10 backdrop-blur-xl border-white/20 text-white hover:bg-white/20 hover:border-white/30" />
                  <CarouselNext className="absolute right-0 top-1/2 -translate-y-1/2 bg-white/10 backdrop-blur-xl border-white/20 text-white hover:bg-white/20 hover:border-white/30" />
                </Carousel>
              )}

              {/* Show questions for all queues */}
              {(user.Question1 || user.Question2 || user.Question3 || (user.MBTI_DESCRIPTION && user.MBTI)) && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-white mb-3">Personal Insights</h3>
                  
                  {user.Question1 && (
                    <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                      <h4 className="text-sm font-medium text-white/90 mb-2">{user.Question1.Question}</h4>
                      <p className="text-white/70 text-sm leading-relaxed">{user.Question1.Answer}</p>
                    </div>
                  )}
                  
                  {user.Question2 && (
                    <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                      <h4 className="text-sm font-medium text-white/90 mb-2">{user.Question2.Question}</h4>
                      <p className="text-white/70 text-sm leading-relaxed">{user.Question2.Answer}</p>
                    </div>
                  )}
                  
                  {user.Question3 && (
                    <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                      <h4 className="text-sm font-medium text-white/90 mb-2">{user.Question3.Question}</h4>
                      <p className="text-white/70 text-sm leading-relaxed">{user.Question3.Answer}</p>
                    </div>
                  )}
                  
                  {/* MBTI Personality Description */}
                  {user.MBTI_DESCRIPTION && user.MBTI && (
                    <div className="bg-gradient-to-r from-purple-500/20 to-indigo-500/20 backdrop-blur-sm rounded-lg p-4 border border-purple-400/30 mt-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-4 h-4 text-purple-300" />
                        <h4 className="text-sm font-medium text-purple-200">Personality Type</h4>
                      </div>
                      <p className="text-white/80 text-sm leading-relaxed">
                        <span className="font-semibold text-purple-300">{user.MBTI}</span>
                        <span className="text-white/60"> : </span>
                        <span className="italic">{user.MBTI_DESCRIPTION}</span>
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </>
    );
  });

  UserCard.displayName = "UserCard";

  const EmptyState = ({ icon: Icon, title, description }: { 
    icon: any; 
    title: string; 
    description: string; 
  }) => (
    <div className="text-center py-20">
      <div className="relative mx-auto mb-6 w-20 h-20">
        <div className="absolute inset-0 bg-gradient-to-br from-violet-500/20 to-purple-500/20 rounded-full blur-xl"></div>
        <div className="relative w-20 h-20 bg-white/10 backdrop-blur-xl rounded-full flex items-center justify-center border border-white/20">
          <Icon className="w-8 h-8 text-white/60" />
        </div>
      </div>
      <h3 className="text-xl font-semibold text-white/90 mb-3">{title}</h3>
      <p className="text-white/60 max-w-md mx-auto leading-relaxed">{description}</p>
    </div>
  );

  const handlePreferenceChat = async () => {
    if (!userUID) return;
    
    try {
      // Try chat:preference endpoint first, fallback to chat:user
      let endpoint = 'chat:preference';
      let response = await fetch(`http://localhost:8040/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Origin': 'http://localhost:8080'
        },
        body: JSON.stringify({
          uid: userUID
        })
      });
      
      // Fallback to chat:user if chat:preference is not available
      if (!response.ok && response.status === 404) {
        console.log('chat:preference not available, falling back to chat:user');
        endpoint = 'chat:user';
        response = await fetch(`http://localhost:8040/${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': 'http://localhost:8080'
          },
          body: JSON.stringify({
            uid: userUID
          })
        });
      }
      
      if (response.ok) {
        const data = await response.json();
        console.log(`Preference chat initiated successfully via ${endpoint}:`, data);
        setChatMessage(data.message);
        
        // Process recommendations if present, especially if filter_applied=true
        await processRecommendationsFromChat(data);
        
        // Add separator for preference chat messages
        addSessionSeparator('chat-type');
        
        // Initialize unified chat state with the preference chat message
        const initialMessage = { 
          text: data.message, 
          isUser: false, 
          timestamp: new Date(),
          type: 'chat:user' as const
        };
        setUnifiedChatMessages(prev => [...prev, initialMessage]);
        setUnifiedChatHistory(data.history || []);
        setShowChat(true);
        setIsPreferenceChat(true);
      } else {
        console.error(`Failed to initiate preference chat via ${endpoint}:`, response.status);
      }
    } catch (error) {
      console.error('Error initiating preference chat:', error);
    }
  };

  const handleChatResponse = async (userInput: string) => {
    if (!userUID) return;
    
    // Track that user has sent a message
    setHasUserSentMessage(true);
    sessionStorage.setItem('destinyUserHasChatted', 'true');
    
    // Add user message to unified chat state
    const userMessage = { 
      text: userInput, 
      isUser: true, 
      timestamp: new Date(),
      type: isPreferenceChat ? 'chat:user' as const : 'chat:app' as const
    };
    setUnifiedChatMessages(prev => [...prev, userMessage]);
    
    try {
      let endpoint = 'chat:app';
      if (isPreferenceChat) {
        endpoint = 'chat:user';
      } else if (isInitialResponse) {
        endpoint = 'chat:app';
      }
      
      const response = await fetch(`http://localhost:8040/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Origin': 'http://localhost:8080'
        },
        body: JSON.stringify({
          uid: userUID,
          user_input: userInput,
          history: unifiedChatHistory
        })
      });

      if (response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const data = await response.json();
          setChatMessage(data.message);
          
          // Process recommendations if present
          await processRecommendationsFromChat(data);
          
          // Add response to unified chat state
          const responseMessage = { 
            text: data.message, 
            isUser: false, 
            timestamp: new Date(),
            type: isPreferenceChat ? 'chat:user' as const : 'chat:app' as const
          };
          setUnifiedChatMessages(prev => [...prev, responseMessage]);
          
          // Add user message and response to unified chat history
          setUnifiedChatHistory(prevHistory => [
            ...prevHistory,
            { text: userInput, isUser: true },
            { text: data.message, isUser: false }
          ]);
          setIsInitialResponse(false);
          
          if (data.continue) {
            setIsWaitingForUser(true);
            // Don't automatically continue - wait for user to click send
          } else {
            // Show final message for 2 seconds then close
            setTimeout(() => {
              setShowChat(false);
              sessionStorage.setItem('destinyChatCompleted', 'true');
            }, 2000);
          }
        } else {
          console.error('Expected JSON response but got:', contentType);
        }
      }
    } catch (error) {
      console.error('Error continuing chat:', error);
    }
  };

  const handleChatExit = async () => {
    if (userUID) {
      try {
        // Determine if this is a preference chat by checking if the chat was initiated by preference button
        const isPreferenceChatExit = showChatWindow;
        const endpoint = isPreferenceChatExit ? 'chat:user' : 'chat:app';
        
        const response = await fetch(`http://localhost:8040/${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Origin': 'http://localhost:8080'
          },
          body: JSON.stringify({
            uid: userUID,
            user_input: "exit",
            history: unifiedChatHistory
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Chat exit handled successfully');
          
          // Process recommendations if present
          await processRecommendationsFromChat(data);
        }
      } catch (error) {
        console.error('Error handling chat exit:', error);
      }
    }
    setShowChat(false);
    setShowChatWindow(false);
    sessionStorage.setItem('destinyChatDismissed', 'true');
  };

  // Callback for when user sends message in ChatWithDestiny
  const handleUserSendMessage = () => {
    setHasUserSentMessage(true);
    setHasUsedChatWithDestiny(true);
    sessionStorage.setItem('destinyUserHasChatted', 'true');
    sessionStorage.setItem(`destinyWindowChatUsed_${userUID}`, 'true');
    console.log('User has started using ChatWithDestiny for chat:user - disabling chat:app popup');
  };

  if (selectedUser) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 overflow-x-hidden">
        <div className="container mx-auto px-4 py-8">
          <ProfileView user={selectedUser as unknown as UserType} onBack={handleBackToList}>
            <UserActions 
              userUID={selectedUser.recommendation_uid} 
              currentUserUID={userUID}
              onActionComplete={handleActionComplete}
            />
          </ProfileView>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 overflow-x-hidden">
      <div className="w-full max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="border-b border-white/10 bg-white/5 backdrop-blur-2xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6 flex items-center justify-between">
          <div className="flex items-center space-x-2 sm:space-x-4">
            <h1 className="text-3xl sm:text-6xl font-bold text-white tracking-tight font-['Lavanderia']">Aligned</h1>
          </div>
          <div className="flex gap-2 sm:gap-3">
            <Popover open={isNotificationsOpen} onOpenChange={(open) => {
              setIsNotificationsOpen(open);
              if (open) setHasNewNotifications(false);
            }}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="relative border-white/20 bg-white/5 backdrop-blur-xl text-white/90 hover:bg-white/10 hover:border-white/30 transition-all duration-300 font-medium text-xs sm:text-sm px-2 sm:px-4"
                >
                  <Bell className={`w-3 h-3 sm:w-4 sm:h-4 sm:mr-2 ${hasNewNotifications ? 'text-yellow-400 animate-pulse' : ''}`} />
                  <span className="hidden sm:inline">Notifications</span>
                  {totalNotificationCount > 0 && (
                    <Badge className="ml-1 sm:ml-2 h-4 w-4 sm:h-5 sm:w-5 p-0 flex items-center justify-center bg-red-500 text-white text-xs">
                      {totalNotificationCount}
                    </Badge>
                  )}
                  {hasNewNotifications && (
                    <span className="absolute top-0 right-0 h-2 w-2 bg-yellow-400 rounded-full animate-ping"></span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-80 p-0 bg-white/5 backdrop-blur-xl border border-white/10" align="end">
                <div className="p-4 border-b border-white/10">
                  <h3 className="font-semibold text-white text-lg">Notifications</h3>
                  <p className="text-white/60 text-sm">Recent system updates</p>
                </div>
                <div className="max-h-96 overflow-y-auto p-4">
                  <div className="space-y-3">
                    {(() => {
                      // Separate new and old system notifications
                      const newSystemNotifications = systemNotifications.filter(n => n.isNew === true);
                      const oldSystemNotifications = systemNotifications.filter(n => n.isNew !== true);
                      
                      // Combine all notifications in the desired order: messages, new notifications, old notifications
                      const allNotifications = [
                        // Map messages to a consistent format (always shown first)
                        ...messages.map(message => ({
                          id: message.id,
                          text: message.text,
                          timestamp: message.timestamp,
                          userName: message.userName,
                          isNew: false,
                          type: 'message'
                        })),
                        // Map new system notifications (shown second, highlighted)
                        ...newSystemNotifications.map((notification, index) => ({
                          id: `new-system-${index}`,
                          text: notification.message,
                          timestamp: new Date(notification.updated),
                          userName: undefined,
                          isNew: true,
                          type: 'system'
                        })),
                        // Map old system notifications (shown last, normal)
                        ...oldSystemNotifications.map((notification, index) => ({
                          id: `old-system-${index}`,
                          text: notification.message,
                          timestamp: new Date(notification.updated),
                          userName: undefined,
                          isNew: false,
                          type: 'system'
                        }))
                      ];

                      // Sort within each group by timestamp (newest first)
                      const sortedNotifications = [
                        ...allNotifications.filter(n => n.type === 'message').sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
                        ...allNotifications.filter(n => n.type === 'system' && n.isNew).sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()),
                        ...allNotifications.filter(n => n.type === 'system' && !n.isNew).sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
                      ];

                      return sortedNotifications.length > 0 ? (
                        sortedNotifications.map((notification) => (
                          <div 
                            key={notification.id} 
                            className={`p-3 rounded-lg border transition-all duration-200 ${
                              notification.isNew 
                                ? 'bg-gradient-to-r from-violet-500/20 to-purple-500/20 border-violet-400/30 shadow-lg shadow-violet-500/10' 
                                : 'bg-white/5 border-white/10'
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="text-white text-sm">{notification.text}</p>
                                {notification.userName && (
                                  <p className="text-white/60 text-xs mt-1">From: {notification.userName}</p>
                                )}
                                <p className="text-white/40 text-xs mt-1">
                                  {formatDistanceToNow(notification.timestamp, { addSuffix: true })}
                                </p>
                              </div>
                              {notification.isNew && (
                                <div className="flex-shrink-0 ml-2">
                                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-violet-500/20 text-violet-300 border border-violet-400/30">
                                    New
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8">
                          <Bell className="w-8 h-8 text-white/40 mx-auto mb-2" />
                          <p className="text-white/60 text-sm">No notifications yet</p>
                          <p className="text-white/40 text-xs mt-1">System updates will appear here</p>
                        </div>
                      );
                    })()}
                  </div>
                </div>
              </PopoverContent>
            </Popover>
            <Button 
              onClick={handleViewProfile}
              variant="outline"
              size="sm"
              className="border-white/20 bg-white/5 backdrop-blur-xl text-white/90 hover:bg-white/10 hover:border-white/30 transition-all duration-300 font-medium text-xs sm:text-sm px-2 sm:px-4"
            >
              <User className="w-3 h-3 sm:w-4 sm:h-4 sm:mr-2" />
              <span className="hidden sm:inline">Profile</span>
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <Tabs value={activeTab} className="space-y-6 sm:space-y-8" onValueChange={updateActiveTab}>
          <TabsList className="grid w-full grid-cols-3 bg-white/5 backdrop-blur-xl border border-white/10 p-1 rounded-2xl">
            <TabsTrigger 
              value="recommendations" 
              className="flex items-center gap-1 sm:gap-2 text-white/70 data-[state=active]:bg-white/10 data-[state=active]:text-white font-medium rounded-xl transition-all duration-300 py-2 sm:py-3 px-2 sm:px-4 text-xs sm:text-sm"
            >
              <Users className="w-4 h-4" />
              <span className="hidden sm:inline">Discover</span>
            </TabsTrigger>
            <TabsTrigger 
              value="awaiting" 
              className="flex items-center gap-1 sm:gap-2 text-white/70 data-[state=active]:bg-white/10 data-[state=active]:text-white font-medium rounded-xl transition-all duration-300 py-2 sm:py-3 px-2 sm:px-4 text-xs sm:text-sm"
            >
              <Clock className="w-4 h-4" />
              <span className="hidden sm:inline">Awaiting</span>
            </TabsTrigger>
            <TabsTrigger 
              value="matches" 
              className="flex items-center gap-1 sm:gap-2 text-white/70 data-[state=active]:bg-white/10 data-[state=active]:text-white font-medium rounded-xl transition-all duration-300 py-2 sm:py-3 px-2 sm:px-4 text-xs sm:text-sm"
            >
              <Heart className="w-4 h-4" />
              <span className="hidden sm:inline">Matches</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="recommendations" className="space-y-6">
            <Card className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
              <CardHeader className="pb-6 bg-gradient-to-r from-violet-500/10 to-purple-500/10">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="absolute -inset-1 bg-gradient-to-r from-violet-500 to-purple-500 rounded-xl blur opacity-30"></div>
                    <div className="relative w-12 h-12 bg-white/10 backdrop-blur-xl rounded-xl border border-white/20 flex items-center justify-center">
                      <Users className="w-6 h-6 text-violet-300" />
                    </div>
                  </div>
                  <div>
                    <CardTitle className="text-white text-xl font-bold">Discover New People</CardTitle>
                    <CardDescription className="text-white/60 font-medium mt-1">
                      Curated profiles that match your cosmic compatibility
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                {isLoading.recommendations ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="text-center">
                      <div className="relative w-16 h-16 mx-auto mb-6">
                        <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-purple-500 rounded-full blur-lg opacity-50"></div>
                        <div className="relative w-16 h-16 bg-white/10 backdrop-blur-xl rounded-full border border-white/20 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/70"></div>
                        </div>
                      </div>
                      <p className="text-white/70 font-medium">Discovering your perfect matches...</p>
                    </div>
                  </div>
                ) : recommendations.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {recommendations.map((user) => (
                      <UserCard 
                        key={`recommendation-${user.recommendation_uid}`} 
                        user={user} 
                        queue="recommendations"
                      />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={Users}
                    title="No recommendations yet"
                    description="We're working on finding your perfect matches. Check back soon!"
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="awaiting" className="space-y-6">
            <Card className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
              <CardHeader className="pb-6 bg-gradient-to-r from-amber-500/10 to-orange-500/10">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="absolute -inset-1 bg-gradient-to-r from-amber-500 to-orange-500 rounded-xl blur opacity-30"></div>
                    <div className="relative w-12 h-12 bg-white/10 backdrop-blur-xl rounded-xl border border-white/20 flex items-center justify-center">
                      <Clock className="w-6 h-6 text-amber-300" />
                    </div>
                  </div>
                  <div>
                    <CardTitle className="text-white text-xl font-bold">Awaiting Response</CardTitle>
                    <CardDescription className="text-white/60 font-medium mt-1">
                      People waiting for your decision
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                {isLoading.awaiting ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="text-center">
                      <div className="relative w-16 h-16 mx-auto mb-6">
                        <div className="absolute inset-0 bg-gradient-to-br from-amber-500 to-orange-500 rounded-full blur-lg opacity-50"></div>
                        <div className="relative w-16 h-16 bg-white/10 backdrop-blur-xl rounded-full border border-white/20 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/70"></div>
                        </div>
                      </div>
                      <p className="text-white/70 font-medium">Loading awaiting responses...</p>
                    </div>
                  </div>
                ) : awaiting.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {awaiting.map((user) => (
                      <UserCard key={`awaiting-${user.recommendation_uid}`} user={user} queue="awaiting" />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={Clock}
                    title="No pending responses"
                    description="You're all caught up with your responses!"
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="matches" className="space-y-6">
            <Card className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
              <CardHeader className="pb-6 bg-gradient-to-r from-pink-500/10 to-red-500/10">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <div className="absolute -inset-1 bg-gradient-to-r from-pink-500 to-red-500 rounded-xl blur opacity-30"></div>
                    <div className="relative w-12 h-12 bg-white/10 backdrop-blur-xl rounded-xl border border-white/20 flex items-center justify-center">
                      <Heart className="w-6 h-6 text-pink-300" />
                    </div>
                  </div>
                  <div>
                    <CardTitle className="text-white text-xl font-bold">Your Matches</CardTitle>
                    <CardDescription className="text-white/60 font-medium mt-1">
                      People who liked you back - it's a match!
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                {isLoading.matches ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="text-center">
                      <div className="relative w-16 h-16 mx-auto mb-6">
                        <div className="absolute inset-0 bg-gradient-to-br from-pink-500 to-red-500 rounded-full blur-lg opacity-50"></div>
                        <div className="relative w-16 h-16 bg-white/10 backdrop-blur-xl rounded-full border border-white/20 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/70"></div>
                        </div>
                      </div>
                      <p className="text-white/70 font-medium">Loading your matches...</p>
                    </div>
                  </div>
                ) : matches.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {matches.map((user) => (
                      <UserCard key={`match-${user.recommendation_uid}`} user={user} queue="matches" />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={Heart}
                    title="No matches yet"
                    description="Keep swiping to find your perfect match! When someone likes you back, they'll appear here."
                  />
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {showChat && userUID && (
          <div className="fixed bottom-6 right-6 z-50">
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="bg-white rounded-lg shadow-xl w-80 sm:w-96 mb-4 border border-indigo-100 flex flex-col max-h-[80vh]"
            >
              <div className="p-4 border-b flex justify-between items-center bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-t-lg">
                <h3 className="font-['Lavanderia'] text-2xl">Destiny</h3>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleChatExit}
                  className="h-8 w-8 hover:bg-indigo-500/20 text-white"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
              <div ref={chatHistoryRef} className="flex-1 overflow-y-auto scroll-smooth p-4 space-y-4 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                {unifiedChatMessages.map((message, index) => (
                  <div 
                    key={index} 
                    className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[80%] rounded-lg p-3 ${
                      message.isUser 
                        ? 'bg-indigo-600 text-white' 
                        : 'bg-indigo-50 text-gray-700'
                    }`}>
                      <p className="text-sm">{message.text}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 border-t">
                <div className="flex gap-2">
                  <Input
                    placeholder="Type your response..."
                    className="flex-1 text-sm border-indigo-100 focus:border-indigo-300 text-gray-900 placeholder:text-gray-500"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleChatResponse(e.currentTarget.value);
                        e.currentTarget.value = '';
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      const input = document.querySelector('input');
                      if (input) {
                        handleChatResponse(input.value);
                        input.value = '';
                      }
                    }}
                    className="bg-gradient-to-br from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white px-4"
                  >
                    Send
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        <div className="fixed bottom-6 right-6 z-40">
        <ChatWithDestiny 
          userUID={userUID}
          onClose={() => {
              setShowChatWindow(false);
          }}
          showChatWindow={showChatWindow}
          onUserSendMessage={handleUserSendMessage}
          onFilterApplied={processRecommendationsFromChat} // Add callback for filter responses
          messages={unifiedChatMessages}
          setMessages={setUnifiedChatMessages}
          history={unifiedChatHistory}
          setHistory={setUnifiedChatHistory}
        />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
