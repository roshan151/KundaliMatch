import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  User, 
  MapPin, 
  Calendar, 
  Clock, 
  Briefcase, 
  Heart,
  Camera,
  Edit,
  Mail,
  Globe,
  Star,
  Sparkles,
  Phone,
  Filter,
  X
} from "lucide-react";
import { getImageUrl, extractS3Key } from "@/lib/utils";
import { config } from "@/config/api";
import { useProfileContext } from "../contexts/ProfileContext";

interface ProfileData {
  uid: string;
  email: string;
  name: string;
  phone?: string;
  gender?: string;
  city?: string;
  country?: string;
  birth_city?: string;
  birth_country?: string;
  profession?: string;
  dob?: string;
  tob?: string;
  hobbies?: string[];
  images?: string[];
  login?: string;
  FILTERS?: string[]; // Added FILTERS field
  MBTI?: string; // Personality type code
  MBTI_DESCRIPTION?: string; // Personality description
  Question1?: { Question: string; Answer: string };
  Question2?: { Question: string; Answer: string };
  Question3?: { Question: string; Answer: string };
}

interface ProfileProps {
  onEdit?: () => void;
  cachedProfileData?: ProfileData | null;
  isLoadingProfile?: boolean;
}

const Profile = ({ onEdit, cachedProfileData, isLoadingProfile }: ProfileProps) => {
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [signedImageUrls, setSignedImageUrls] = useState<string[]>([]);
  const [removingFilters, setRemovingFilters] = useState<Set<string>>(new Set());
  
  const { profileData: contextProfileData, isRefreshing } = useProfileContext();

  useEffect(() => {
    // Priority 1: Use context profile data if available (refreshed data)
    if (contextProfileData) {
      console.log('Using refreshed profile data from context:', contextProfileData);
      setProfileData(contextProfileData);
      processImages(contextProfileData.images || []);
      setIsLoading(false);
      return;
    }

    // Priority 2: Use cached data if available
    if (cachedProfileData) {
      console.log('Using cached profile data:', cachedProfileData);
      setProfileData(cachedProfileData);
      processImages(cachedProfileData.images || []);
      setIsLoading(false);
      return;
    }

    // Priority 3: Fallback to localStorage if no cached data
    const storedProfileData = localStorage.getItem('profileData');
    if (storedProfileData) {
      try {
        const parsedData = JSON.parse(storedProfileData);
        console.log('Using stored profile data:', parsedData);
        setProfileData(parsedData);
        processImages(parsedData.images || []);
      } catch (error) {
        console.error('Error parsing stored profile data:', error);
      }
    }
    
    setIsLoading(false);
  }, [cachedProfileData, contextProfileData]);

  const processImages = (images: string[]) => {
    if (!images || images.length === 0) return;

    const proxyUrls = images.map((url) => {
      return getImageUrl(url); // Use backend proxy for secure image access
    });

    setSignedImageUrls(proxyUrls);
  };

  // Show loading if we're explicitly loading profile data
  if (isLoadingProfile || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-purple-500 rounded-full blur-lg opacity-50 animate-pulse"></div>
            <div className="relative w-16 h-16 bg-white/10 backdrop-blur-xl rounded-full border border-white/20 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/70"></div>
            </div>
          </div>
          <p className="text-white/70 font-medium">Loading your amazing profile...</p>
        </div>
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <Card className="max-w-md w-full border-white/10 bg-white/5 backdrop-blur-xl">
          <CardContent className="p-6 text-center">
            <User className="w-12 h-12 text-white/50 mx-auto mb-4" />
            <p className="text-white/70">No profile data available</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const calculateAge = (dob: string) => {
    const birthDate = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  const formatTime = (timeString: string) => {
    if (!timeString) return '';
    const [hours, minutes] = timeString.split(':');
    const time = new Date();
    time.setHours(parseInt(hours), parseInt(minutes));
    return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDateOfBirth = (dateString: string) => {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString; // Return original if invalid date
    
    const day = date.getDate();
    const month = date.toLocaleString('en-US', { month: 'long' });
    const year = date.getFullYear();
    
    // Add ordinal suffix to day
    const getOrdinalSuffix = (day: number) => {
      if (day > 3 && day < 21) return 'th';
      switch (day % 10) {
        case 1: return 'st';
        case 2: return 'nd';
        case 3: return 'rd';
        default: return 'th';
      }
    };
    
    return `${day}${getOrdinalSuffix(day)} ${month}, ${year}`;
  };

  const handleEditProfile = () => {
    if (onEdit) {
      onEdit();
    }
  };

  const handleUploadPhotos = () => {
    // This will be handled by the parent component (ProfilePage)
    if (onEdit) {
      onEdit();
    }
  };

  const removeFilter = async (filterToRemove: string) => {
    if (!profileData?.uid) return;
    
    // Add filter to loading state
    setRemovingFilters(prev => new Set(prev.add(filterToRemove)));
    
    try {
      console.log('Removing filter:', filterToRemove);
      
      const response = await fetch(`${config.URL}/update:filter`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          uid: profileData.uid,
          filter: filterToRemove
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Filter removal response:', data);
        
        // Update local profile data by removing the filter
        setProfileData(prevData => {
          if (!prevData) return prevData;
          const updatedData = {
            ...prevData,
            FILTERS: prevData.FILTERS?.filter(filter => filter !== filterToRemove) || []
          };
          
          // Update localStorage as well
          localStorage.setItem('profileData', JSON.stringify(updatedData));
          return updatedData;
        });

        // If the response contains recommendations, update the cache
        if (data.RECOMMENDATIONS && Array.isArray(data.RECOMMENDATIONS)) {
          console.log('Updating recommendations cache with:', data.RECOMMENDATIONS);
          
          // Clear the existing dashboard data cache to force refresh
          localStorage.removeItem('dashboardData');
          
          // Store the new recommendations in a way that Dashboard can pick them up
          localStorage.setItem('updatedRecommendations', JSON.stringify(data.RECOMMENDATIONS));
          localStorage.setItem('recommendationsCacheTimestamp', Date.now().toString());
        }
        
      } else {
        console.error('Failed to remove filter:', response.status);
      }
    } catch (error) {
      console.error('Error removing filter:', error);
    } finally {
      // Remove filter from loading state
      setRemovingFilters(prev => {
        const newSet = new Set(prev);
        newSet.delete(filterToRemove);
        return newSet;
      });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 overflow-x-hidden">
      <div className="w-full max-w-7xl mx-auto px-4 py-8">
        {/* Enhanced Hero Section */}
        <div className="relative mb-12 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-violet-600/20 via-purple-600/20 to-pink-600/20 rounded-3xl blur-xl"></div>
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-white/5 rounded-3xl backdrop-blur-3xl border border-white/20"></div>
          
          <div className="relative p-8 md:p-12">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-8">
              {/* Enhanced Profile Picture */}
              <div className="relative group">
                <div className="absolute -inset-4 bg-gradient-to-r from-violet-500 via-purple-500 to-pink-500 rounded-full blur-xl opacity-30 group-hover:opacity-50 transition-opacity duration-500"></div>
                <div className="absolute -inset-2 bg-gradient-to-r from-violet-400 to-purple-400 rounded-full blur opacity-20"></div>
                <Avatar className="relative w-36 h-36 md:w-44 md:h-44 ring-4 ring-white/30 shadow-2xl transform group-hover:scale-105 transition-all duration-500">
                  <AvatarImage 
                    src={signedImageUrls[0] || profileData?.images?.[0]} 
                    className="object-cover"
                  />
                  <AvatarFallback className="bg-gradient-to-br from-violet-500 via-purple-500 to-pink-500 text-white text-4xl font-bold">
                    {profileData?.name?.charAt(0) || <User className="w-20 h-20" />}
                  </AvatarFallback>
                </Avatar>
                {profileData?.images && profileData.images.length > 1 && (
                  <Badge className="absolute -bottom-2 -right-2 bg-gradient-to-r from-violet-500 to-purple-500 shadow-lg border-0">
                    <Camera className="w-3 h-3 mr-1" />
                    {profileData.images.length}
                  </Badge>
                )}
                <div className="absolute top-2 right-2 w-4 h-4 bg-green-400 rounded-full border-2 border-white shadow-lg animate-pulse"></div>
              </div>

              {/* Enhanced Profile Info */}
              <div className="flex-1 text-center md:text-left">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between mb-8">
                  <div>
                    <div className="flex items-center justify-center md:justify-start gap-3 mb-3">
                      <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-white via-violet-200 to-purple-200 bg-clip-text text-transparent">
                        {profileData?.name}
                      </h1>
                      <Sparkles className="w-8 h-8 text-violet-400 animate-pulse" />
                    </div>
                    
                    {/* Profile Refresh Indicator */}
                    {isRefreshing && (
                      <div className="flex items-center justify-center md:justify-start gap-2 mb-4 animate-pulse">
                        <div className="w-4 h-4 bg-violet-400 rounded-full animate-spin border-2 border-white border-t-transparent"></div>
                        <p className="text-sm text-violet-300 font-medium">
                          Updating profile with new filters...
                        </p>
                      </div>
                    )}
                    <div className="flex items-center justify-center md:justify-start gap-2 mb-4">
                      <Star className="w-5 h-5 text-yellow-400" />
                      <p className="text-xl text-white/80 font-medium">
                        {profileData?.profession || 'Amazing Individual'}
                      </p>
                    </div>
                  </div>
                  {onEdit && (
                    <Button 
                      onClick={handleEditProfile} 
                      size="lg"
                      className="mt-4 md:mt-0 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-300"
                    >
                      <Edit className="w-5 h-5 mr-2" />
                      Edit Profile
                    </Button>
                  )}
                </div>

                {/* Enhanced Quick Stats */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {profileData?.dob && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/20 hover:bg-white/15 transition-all duration-300 group">
                      <div className="flex items-center justify-center md:justify-start gap-3">
                        <div className="p-2 bg-violet-500/20 rounded-full group-hover:bg-violet-500/30 transition-colors">
                          <Calendar className="w-5 h-5 text-violet-300" />
                        </div>
                        <div>
                          <p className="text-sm text-white/60 font-medium">Age</p>
                          <p className="text-lg font-bold text-white">{calculateAge(profileData.dob)}</p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {profileData?.city && profileData.country && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/20 hover:bg-white/15 transition-all duration-300 group min-h-[80px] sm:min-h-[72px]">
                      <div className="flex items-start justify-center md:justify-start gap-3 h-full">
                        <div className="p-2 bg-blue-500/20 rounded-full group-hover:bg-blue-500/30 transition-colors flex-shrink-0">
                          <MapPin className="w-5 h-5 text-blue-300" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm text-white/60 font-medium">Location</p>
                          <p className="text-sm font-bold text-white break-words leading-tight">{profileData.city}, {profileData.country}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {profileData?.profession && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/20 hover:bg-white/15 transition-all duration-300 group">
                      <div className="flex items-center justify-center md:justify-start gap-3">
                        <div className="p-2 bg-emerald-500/20 rounded-full group-hover:bg-emerald-500/30 transition-colors">
                          <Briefcase className="w-5 h-5 text-emerald-300" />
                        </div>
                        <div>
                          <p className="text-sm text-white/60 font-medium">Career</p>
                          <p className="text-sm font-bold text-white">{profileData.profession}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {profileData?.MBTI && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/20 hover:bg-white/15 transition-all duration-300 group">
                      <div className="flex items-center justify-center md:justify-start gap-3">
                        <div className="p-2 bg-purple-500/20 rounded-full group-hover:bg-purple-500/30 transition-colors">
                          <Sparkles className="w-5 h-5 text-purple-300" />
                        </div>
                        <div>
                          <p className="text-sm text-white/60 font-medium">Personality</p>
                          <p className="text-sm font-bold text-purple-300">{profileData.MBTI}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {profileData?.tob && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-4 border border-white/20 hover:bg-white/15 transition-all duration-300 group">
                      <div className="flex items-center justify-center md:justify-start gap-3">
                        <div className="p-2 bg-pink-500/20 rounded-full group-hover:bg-pink-500/30 transition-colors">
                          <Clock className="w-5 h-5 text-pink-300" />
                        </div>
                        <div>
                          <p className="text-sm text-white/60 font-medium">Born</p>
                          <p className="text-sm font-bold text-white">{formatTime(profileData.tob)}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Enhanced Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Enhanced Personal Information */}
            <Card className="border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
              <CardHeader className="pb-6">
                <CardTitle className="flex items-center text-2xl bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">
                  <div className="p-3 bg-violet-500/20 rounded-xl mr-4 group-hover:bg-violet-500/30 transition-colors">
                    <User className="w-6 h-6 text-violet-300" />
                  </div>
                  Personal Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="bg-white/10 backdrop-blur-xl rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300">
                    <div className="flex items-center gap-3 mb-3">
                      <Mail className="w-5 h-5 text-violet-400" />
                      <label className="text-sm font-bold text-violet-200 uppercase tracking-wider">Email</label>
                    </div>
                    <p className="text-lg text-white font-medium">{profileData?.email || 'Not provided'}</p>
                  </div>

                  <div className="bg-white/10 backdrop-blur-xl rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300">
                    <div className="flex items-center gap-3 mb-3">
                      <Phone className="w-5 h-5 text-green-400" />
                      <label className="text-sm font-bold text-green-200 uppercase tracking-wider">Phone</label>
                    </div>
                    <p className="text-lg text-white font-medium">{profileData?.phone || 'Not provided'}</p>
                  </div>
                  
                  {profileData?.gender && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300">
                      <div className="flex items-center gap-3 mb-3">
                        <User className="w-5 h-5 text-pink-400" />
                        <label className="text-sm font-bold text-pink-200 uppercase tracking-wider">Gender</label>
                      </div>
                      <p className="text-lg text-white font-medium capitalize">{profileData.gender}</p>
                    </div>
                  )}

                  {profileData?.dob && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300">
                      <div className="flex items-center gap-3 mb-3">
                        <Calendar className="w-5 h-5 text-blue-400" />
                        <label className="text-sm font-bold text-blue-200 uppercase tracking-wider">Date of Birth</label>
                      </div>
                      <p className="text-lg text-white font-medium">{formatDateOfBirth(profileData.dob)}</p>
                    </div>
                  )}

                  {profileData?.birth_city && profileData.birth_country && (
                    <div className="bg-white/10 backdrop-blur-xl rounded-xl p-6 border border-white/20 hover:bg-white/15 transition-all duration-300">
                      <div className="flex items-center gap-3 mb-3">
                        <Globe className="w-5 h-5 text-emerald-400" />
                        <label className="text-sm font-bold text-emerald-200 uppercase tracking-wider">Birth Place</label>
                      </div>
                      <p className="text-lg text-white font-medium">{profileData.birth_city}, {profileData.birth_country}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Enhanced Photo Gallery with Better Visibility */}
            <Card className="border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
              <CardHeader className="pb-6">
                <CardTitle className="flex items-center justify-between text-2xl bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">
                  <div className="flex items-center">
                    <div className="p-3 bg-violet-500/20 rounded-xl mr-4 group-hover:bg-violet-500/30 transition-colors">
                      <Camera className="w-6 h-6 text-violet-300" />
                    </div>
                    Photo Gallery
                  </div>
                  {profileData?.images && profileData.images.length > 0 && (
                    <Badge variant="secondary" className="bg-gradient-to-r from-violet-500/30 to-purple-500/30 text-white border-violet-400/50 font-semibold">
                      {profileData.images.length} photos
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {profileData?.images && profileData.images.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                    {signedImageUrls.map((image, index) => {
                      if (!image || image.length === 0) return null;
                      
                      return (
                        <div key={index} className="relative aspect-square overflow-hidden rounded-2xl bg-slate-800/50 group cursor-pointer transform hover:scale-105 transition-all duration-500 shadow-xl hover:shadow-2xl border border-white/20">
                          {/* Enhanced overlay for better visibility */}
                          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10"></div>
                          <div className="absolute bottom-3 left-3 right-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <p className="text-white text-sm font-semibold bg-black/30 backdrop-blur-sm rounded-lg px-3 py-1">
                              Photo {index + 1}
                            </p>
                          </div>
                          <img
                            src={image}
                            alt={`Photo ${index + 1}`}
                            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                            onError={(e) => {
                              const target = e.currentTarget;
                              target.style.display = 'none';
                              const parent = target.parentElement;
                              if (parent) {
                                parent.innerHTML = `
                                  <div class="w-full h-full flex items-center justify-center bg-slate-800/70 text-white/80 border border-white/30 rounded-2xl backdrop-blur-xl">
                                    <div class="text-center p-4">
                                      <svg class="w-12 h-12 mx-auto mb-3 text-violet-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
                                      </svg>
                                      <p class="text-sm font-semibold text-white">Photo ${index + 1}</p>
                                      <p class="text-xs text-white/60 mt-1">Image unavailable</p>
                                    </div>
                                  </div>
                                `;
                              }
                            }}
                          />
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-16">
                    <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-violet-500/20 to-purple-500/20 flex items-center justify-center border border-white/20">
                      <Camera className="w-10 h-10 text-violet-400" />
                    </div>
                    <p className="text-white/70 text-lg font-medium">No photos uploaded yet</p>
                    <p className="text-white/50 text-sm mt-2">Share your moments with the world</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Personal Insights - Questions & Answers */}
            {(profileData?.Question1 || profileData?.Question2 || profileData?.Question3 || (profileData?.MBTI_DESCRIPTION && profileData?.MBTI)) && (
              <Card className="border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
                <CardHeader className="pb-6">
                  <CardTitle className="flex items-center text-2xl bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">
                    <div className="p-3 bg-emerald-500/20 rounded-xl mr-4 group-hover:bg-emerald-500/30 transition-colors">
                      <Heart className="w-6 h-6 text-emerald-300" />
                    </div>
                    Personal Insights
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {profileData?.Question1 && (
                    <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10 hover:bg-white/10 transition-all duration-300">
                      <h4 className="text-lg font-semibold text-emerald-200 mb-3">{profileData.Question1.Question}</h4>
                      <p className="text-white/80 leading-relaxed">{profileData.Question1.Answer}</p>
                    </div>
                  )}
                  
                  {profileData?.Question2 && (
                    <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10 hover:bg-white/10 transition-all duration-300">
                      <h4 className="text-lg font-semibold text-emerald-200 mb-3">{profileData.Question2.Question}</h4>
                      <p className="text-white/80 leading-relaxed">{profileData.Question2.Answer}</p>
                    </div>
                  )}
                  
                  {profileData?.Question3 && (
                    <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10 hover:bg-white/10 transition-all duration-300">
                      <h4 className="text-lg font-semibold text-emerald-200 mb-3">{profileData.Question3.Question}</h4>
                      <p className="text-white/80 leading-relaxed">{profileData.Question3.Answer}</p>
                    </div>
                  )}
                  
                  {/* MBTI Personality Description */}
                  {profileData?.MBTI_DESCRIPTION && profileData?.MBTI && (
                    <div className="bg-gradient-to-r from-purple-500/20 to-indigo-500/20 backdrop-blur-sm rounded-xl p-6 border border-purple-400/30">
                      <div className="flex items-center gap-3 mb-3">
                        <Sparkles className="w-5 h-5 text-purple-300" />
                        <h4 className="text-lg font-semibold text-purple-200">Personality Type</h4>
                      </div>
                      <p className="text-white/80 leading-relaxed">
                        <span className="font-semibold text-purple-300">{profileData.MBTI}</span>
                        <span className="text-white/60"> : </span>
                        <span className="italic">{profileData.MBTI_DESCRIPTION}</span>
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Enhanced Sidebar with Better Interests Visibility */}
          <div className="space-y-8">
            {/* Enhanced Interests & Hobbies with Improved Visibility */}
            <Card className="border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
              <CardHeader className="pb-6">
                <CardTitle className="flex items-center text-2xl bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">
                  <div className="p-3 bg-pink-500/20 rounded-xl mr-4 group-hover:bg-pink-500/30 transition-colors">
                    <Heart className="w-6 h-6 text-pink-300" />
                  </div>
                  Interests & Hobbies
                </CardTitle>
              </CardHeader>
              <CardContent>
                {profileData?.hobbies && profileData.hobbies.length > 0 ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-3">
                      {profileData.hobbies.map((hobby, index) => (
                        <Badge 
                          key={index} 
                          className="px-4 py-3 rounded-full text-sm font-bold bg-gradient-to-r from-blue-500/60 to-cyan-500/60 text-white border-2 border-blue-400/80 hover:from-blue-500/70 hover:to-cyan-500/70 hover:border-blue-400/90 hover:scale-105 transition-all duration-300 cursor-pointer shadow-lg backdrop-blur-xl"
                        >
                          {hobby}
                        </Badge>
                      ))}
                    </div>
                    <div className="mt-6 p-4 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-xl border border-blue-400/40">
                      <div className="flex items-center gap-2 mb-2">
                        <Heart className="w-4 h-4 text-blue-300" />
                        <span className="text-sm font-semibold text-blue-100">Total Interests</span>
                      </div>
                      <p className="text-2xl font-bold text-white">{profileData.hobbies.length}</p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500/30 to-cyan-500/30 flex items-center justify-center border border-white/20">
                      <Heart className="w-8 h-8 text-blue-300" />
                    </div>
                    <p className="text-white/80 font-semibold text-lg">No interests listed</p>
                    <p className="text-white/60 text-sm mt-2">Add some to let others know what you love</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Enhanced Filters Section */}
            <Card className="border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
              <CardHeader className="pb-6">
                <CardTitle className="flex items-center text-2xl bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">
                  <div className="p-3 bg-blue-500/20 rounded-xl mr-4 group-hover:bg-blue-500/30 transition-colors">
                    <Filter className="w-6 h-6 text-blue-300" />
                  </div>
                  Filters
                </CardTitle>
              </CardHeader>
              <CardContent>
                {profileData?.FILTERS && profileData.FILTERS.length > 0 ? (
                  <div className="space-y-4">
                    <div className="space-y-3">
                      {profileData.FILTERS.map((filter, index) => (
                        <div 
                          key={index} 
                          className={`group relative flex items-center gap-4 p-4 rounded-xl bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-400/30 transition-all duration-300 backdrop-blur-xl ${
                            removingFilters.has(filter) 
                              ? 'opacity-75 cursor-wait' 
                              : 'hover:from-blue-500/30 hover:to-cyan-500/30 hover:border-blue-400/50'
                          }`}
                        >
                          <div className="flex items-center justify-center w-8 h-8 bg-blue-500/30 rounded-full border border-blue-400/50">
                            <span className="text-sm font-bold text-blue-200">{index + 1}</span>
                          </div>
                          <p className="text-white font-medium flex-1">{filter}</p>
                          
                          {/* Cross button or loading spinner */}
                          {removingFilters.has(filter) ? (
                            <div className="absolute top-2 right-2 flex items-center justify-center w-6 h-6 bg-blue-500/80 rounded-full border border-blue-400/50 shadow-lg">
                              <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            </div>
                          ) : (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeFilter(filter);
                              }}
                              className="opacity-0 group-hover:opacity-100 absolute top-2 right-2 flex items-center justify-center w-6 h-6 bg-red-500/80 hover:bg-red-500 rounded-full border border-red-400/50 hover:border-red-400 transition-all duration-200 hover:scale-110 shadow-lg hover:shadow-red-500/25"
                              title="Remove filter"
                              disabled={removingFilters.has(filter)}
                            >
                              <X className="w-3 h-3 text-white" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="mt-6 p-4 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-xl border border-blue-400/30">
                      <div className="flex items-center gap-2 mb-2">
                        <Filter className="w-4 h-4 text-blue-400" />
                        <span className="text-sm font-semibold text-blue-200">Total Filters</span>
                      </div>
                      <p className="text-2xl font-bold text-white">{profileData.FILTERS.length}</p>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center border border-white/20">
                      <Filter className="w-8 h-8 text-blue-400" />
                    </div>
                    <p className="text-white/80 font-semibold text-lg">No filters set</p>
                    <p className="text-white/60 text-sm mt-2">Add filters to customize your preferences</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Enhanced Quick Actions */}
            <Card className="border-0 shadow-2xl bg-white/10 backdrop-blur-xl border border-white/20 hover:shadow-3xl transition-all duration-500 group">
              <CardHeader className="pb-6">
                <CardTitle className="text-2xl bg-gradient-to-r from-white to-violet-200 bg-clip-text text-transparent">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button 
                  variant="outline" 
                  className="w-full justify-start bg-gradient-to-r from-violet-500/20 to-purple-500/20 border-2 border-violet-400/50 text-white hover:from-violet-500/30 hover:to-purple-500/30 hover:border-violet-400/70 hover:scale-105 transition-all duration-300 shadow-lg backdrop-blur-xl font-semibold"
                  onClick={handleUploadPhotos}
                >
                  <Camera className="w-5 h-5 mr-3" />
                  Upload Photos
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
