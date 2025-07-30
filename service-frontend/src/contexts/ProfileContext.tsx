import React, { createContext, useContext, useState } from 'react';
import { config } from '../config/api';

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
  FILTERS?: string[];
  MBTI?: string;
  MBTI_DESCRIPTION?: string;
  Question1?: { Question: string; Answer: string };
  Question2?: { Question: string; Answer: string };
  Question3?: { Question: string; Answer: string };
}

interface ProfileContextType {
  profileData: ProfileData | null;
  setProfileData: React.Dispatch<React.SetStateAction<ProfileData | null>>;
  refreshProfile: (userUID: string) => Promise<void>;
  isRefreshing: boolean;
}

const ProfileContext = createContext<ProfileContextType | undefined>(undefined);

export const ProfileProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const transformUserData = (data: any): ProfileData => {
    console.log('Transforming user data for profile refresh:', data);
    
    let hobbies: string[] = [];
    if (data.HOBBIES || data.hobbies) {
      try {
        const hobbiesData = data.HOBBIES || data.hobbies;
        const hobbiesArray = typeof hobbiesData === 'string' ? JSON.parse(hobbiesData) : hobbiesData;
        hobbies = Array.isArray(hobbiesArray) ? hobbiesArray : hobbiesData.split(',').map((h: string) => h.trim());
      } catch {
        hobbies = typeof (data.HOBBIES || data.hobbies) === 'string' 
          ? (data.HOBBIES || data.hobbies).split(',').map((h: string) => h.trim()) 
          : [];
      }
    }

    // Handle FILTERS field
    let filters: string[] = [];
    if (data.FILTERS || data.filters) {
      try {
        const filtersData = data.FILTERS || data.filters;
        if (Array.isArray(filtersData)) {
          filters = filtersData;
        } else if (typeof filtersData === 'string') {
          // If it's a JSON string, parse it
          if (filtersData.startsWith('[') || filtersData.startsWith('{')) {
            filters = JSON.parse(filtersData);
          } else {
            // If it's comma-separated, split it
            filters = filtersData.split(',').map((f: string) => f.trim());
          }
        }
      } catch (error) {
        console.error('Error parsing FILTERS data:', error);
        filters = [];
      }
    }

    let dob = '';
    if (data.DOB || data.dob) {
      try {
        const dobData = data.DOB || data.dob;
        if (typeof dobData === 'string' && dobData.includes('{')) {
          const dobObj = JSON.parse(dobData);
          dob = `${dobObj.year}-${String(dobObj.month).padStart(2, '0')}-${String(dobObj.day).padStart(2, '0')}`;
        } else {
          dob = dobData;
        }
      } catch {
        dob = data.DOB || data.dob || '';
      }
    }

    return {
      uid: data.UID || data.uid || '',
      email: data.EMAIL || data.email || '',
      name: data.NAME || data.name || '',
      phone: data.PHONE || data.phone || '',
      gender: data.GENDER || data.gender || '',
      city: data.CITY || data.city || '',
      country: data.COUNTRY || data.country || '',
      birth_city: data.BIRTH_CITY || data.birth_city || '',
      birth_country: data.BIRTH_COUNTRY || data.birth_country || '',
      profession: data.PROFESSION || data.profession || '',
      dob: dob,
      tob: data.TOB || data.tob || '',
      hobbies: hobbies,
      images: data.IMAGES || data.images || [],
      FILTERS: filters,
      MBTI: data.MBTI || data.mbti || '',
      MBTI_DESCRIPTION: data.MBTI_DESCRIPTION || data.mbti_description || '',
      Question1: data.Question1 || {},
      Question2: data.Question2 || {},
      Question3: data.Question3 || {}
    };
  };

  const fetchUserProfile = async (uid: string) => {
    try {
      console.log(`Fetching profile for UID: ${uid}`);
      const response = await fetch(`${config.URL}${config.ENDPOINTS.GET_PROFILE}/${uid}`, {
        method: 'GET',
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Fetched user profile for refresh:', data);
        return data;
      } else {
        console.error('Error fetching user profile:', response.status);
        return null;
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      return null;
    }
  };

  const refreshProfile = async (userUID: string) => {
    if (!userUID) {
      console.error('No userUID provided for profile refresh');
      return;
    }

    console.log(`Refreshing profile data for user: ${userUID} due to filter_applied=true`);
    setIsRefreshing(true);

    try {
      // Fetch fresh profile data from API
      const freshProfileData = await fetchUserProfile(userUID);
      
      if (freshProfileData) {
        // Transform the fresh data
        const transformedProfileData = transformUserData(freshProfileData);
        
        // Preserve email and phone from existing localStorage if available
        const existingData = localStorage.getItem('profileData');
        if (existingData) {
          try {
            const parsedExisting = JSON.parse(existingData);
            transformedProfileData.email = transformedProfileData.email || parsedExisting.email;
            transformedProfileData.phone = transformedProfileData.phone || parsedExisting.phone;
          } catch (error) {
            console.error('Error parsing existing profile data:', error);
          }
        }
        
        console.log('Refreshed profile data with new filters:', transformedProfileData);
        
        // Update context state
        setProfileData(transformedProfileData);
        
        // Update localStorage
        localStorage.setItem('profileData', JSON.stringify(transformedProfileData));
        localStorage.setItem('userData', JSON.stringify(transformedProfileData));
        
        console.log('Profile refresh completed successfully');
      } else {
        console.error('Failed to fetch fresh profile data');
      }
    } catch (error) {
      console.error('Error refreshing profile:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const value = {
    profileData,
    setProfileData,
    refreshProfile,
    isRefreshing,
  };

  return (
    <ProfileContext.Provider value={value}>
      {children}
    </ProfileContext.Provider>
  );
};

export const useProfileContext = () => {
  const context = useContext(ProfileContext);
  if (context === undefined) {
    throw new Error('useProfileContext must be used within a ProfileProvider');
  }
  return context;
}; 