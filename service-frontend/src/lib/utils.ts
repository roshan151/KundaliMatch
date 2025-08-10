import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Backend API base URL - use Vite environment variables
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Function to get image URL through backend proxy (more secure than direct S3 access)
export const getImageUrl = (s3Url: string): string => {
  try {
    // Extract S3 key from full S3 URL
    const key = extractS3Key(s3Url);
    if (key) {
      // Use backend image proxy endpoint
      return `${API_BASE_URL}/image/${encodeURIComponent(key)}`;
    }
    return s3Url; // Fallback to original URL
  } catch (error) {
    console.error('Error generating image URL:', error);
    return s3Url;
  }
};

// Function to extract key from S3 URL
export const extractS3Key = (url: string): string | null => {
  const match = url.match(/amazonaws\.com\/(.+)/);
  return match ? match[1] : null;
};

// Legacy function for backward compatibility (now uses backend proxy)
export const getSignedS3Url = async (key: string): Promise<string | null> => {
  try {
    // Use backend image proxy instead of direct S3 access
    return `${API_BASE_URL}/image/${encodeURIComponent(key)}`;
  } catch (error) {
    console.error('Error generating image URL:', error);
    return null;
  }
};
