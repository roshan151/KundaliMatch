import { useState, useEffect } from 'react';
import { getSignedS3Url } from '../lib/utils';

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
        
        const [logo, loginBackground, chatBackground, contentBackground] = await Promise.all([
          getSignedS3Url('frontend/logo.png'),
          getSignedS3Url('frontend/login_page_bg.png'),
          getSignedS3Url('frontend/chat_background.png'),
          getSignedS3Url('frontend/content_background.png'),
        ]);

        setAssets({
          logo,
          loginBackground,
          chatBackground,
          contentBackground,
        });
      } catch (err) {
        console.error('Error loading S3 assets:', err);
        setError('Failed to load assets');
      } finally {
        setLoading(false);
      }
    };

    loadAssets();
  }, []);

  return { assets, loading, error };
}; 