export const config = {
  URL: import.meta.env.VITE_API_URL || 'http://localhost:8040',
  PROFILE_URL: import.meta.env.VITE_PROFILE_API_URL || 'http://localhost:8080',
  MAX_IMAGES: 5,
  ENDPOINTS: {
    CREATE_ACCOUNT: '/account:create',
    VERIFY_EMAIL: '/verify:email',
    GET_PROFILE: '/get:profile',
    FIND_PROFILE: '/get:profile',
    UPDATE_PROFILE: '/update:profile'
  }
};

// Configure fetch to work with different environments
if (import.meta.env.DEV) {
  // For development, we'll handle CORS and local requests
  console.log('Development mode: Using backend at', config.URL);
  console.log('Profile API at', config.PROFILE_URL);
} else {
  // Production mode
  console.log('Production mode: Using backend at', config.URL);
  console.log('Profile API at', config.PROFILE_URL);
}
