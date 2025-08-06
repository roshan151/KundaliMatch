import { useState, useEffect } from 'react';

// Backend API base URL - use Vite environment variables
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8040';

interface S3Assets {
  logo: string | null;
  loginBackground: string | null;
  chatBackground: string | null;
  contentBackground: string | null;
}

export const useS3Assets = () => {
  const [assets, setAssets] = useState<S3Assets>({
    logo: null,
    loginBackground: null,
    chatBackground: null,
    contentBackground: null,
  });
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAssets = async () => {
      try {
        setLoading(true);
        
        // Use backend image proxy endpoints instead of direct S3 access
        setAssets({
          logo: `${API_BASE_URL}/image/frontend/logo.png`,
          loginBackground: `${API_BASE_URL}/image/frontend/login_page_bg.png`,
          chatBackground: `${API_BASE_URL}/image/frontend/chat_background.png`,
          contentBackground: `${API_BASE_URL}/image/frontend/content_background.png`,
        });
      } catch (err) {
        console.error('Error loading assets:', err);
        setError('Failed to load assets');
      } finally {
        setLoading(false);
      }
    };

    loadAssets();
  }, []);

  return { assets, loading, error };
}; 