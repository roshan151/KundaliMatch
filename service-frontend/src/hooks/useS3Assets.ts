import { useState, useEffect } from 'react';

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
        
        // Use local static assets from public folder
        // Vite serves files from public/ directory at the root path
        setAssets({
          logo: '/logo.png',
          loginBackground: '/login_page_bg.png',
          chatBackground: '/chat_background.png',
          contentBackground: '/content_background.png',
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