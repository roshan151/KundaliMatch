export interface User {
  uid: string;
  name: string;
  email?: string;
  phone?: string;
  city?: string;
  country?: string;
  age?: number;
  gender?: string;
  hobbies?: string | string[];
  profilePicture?: string;
  bio?: string;
  images?: string[];
  kundliScore?: number;
  user_align?: boolean;
  reason?: string;
  filtered?: boolean;
}

export interface Notification {
  uid: string;
  name: string;
  message: string;
  timestamp: string;
  updated: string;
  isNew?: boolean;
}

export interface DashboardData {
  recommendations: User[];
  matches: User[];
  awaiting: User[];
  notifications: Notification[];
}

export interface ProfileData {
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
  kundliScore?: number;
  user_align?: boolean;
  FILTERS?: string[]; // Added FILTERS field
  MBTI?: string; // Personality type code
  MBTI_DESCRIPTION?: string; // Personality description
  Question1?: { Question: string; Answer: string };
  Question2?: { Question: string; Answer: string };
  Question3?: { Question: string; Answer: string };
} 