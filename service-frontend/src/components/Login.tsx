import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Mail, Heart, Lock, Eye, EyeOff } from "lucide-react";
import { config } from "../config/api";
import { useToast } from "@/components/ui/use-toast";
import { useS3Assets } from "../hooks/useS3Assets";

interface LoginProps {
  setIsLoggedIn: (value: boolean) => void;
  setUserUID: (uid: string) => void;
  onSuccessfulLogin: (uid: string, loginData: any) => void;
}

const Login = ({ setIsLoggedIn, setUserUID, onSuccessfulLogin }: LoginProps) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const { toast } = useToast();
  const { assets } = useS3Assets();

  const fetchUserProfile = async (uid: string) => {
    try {
      console.log(`Fetching user profile for UID: ${uid}`);

      const response = await fetch(`${config.URL}${config.ENDPOINTS.GET_PROFILE}/${uid}`, {
        method: 'GET',
      });

      if (response.ok) {
        const profileData = await response.json();
        console.log('User profile fetched successfully:', profileData);
        return profileData;
      } else {
        console.error(`Failed to fetch user profile, status: ${response.status}`);
        return null;
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      return null;
    }
  };

  const safeSetLocalStorage = (key: string, value: string) => {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (error) {
      console.error('LocalStorage quota exceeded:', error);
      toast({
        title: "Storage Warning",
        description: "Unable to cache user data. You may need to login again after closing the browser.",
        variant: "destructive"
      });
      return false;
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      console.log('Attempting login with email:', email);
      
      const loginPayload = { email, password };
      
      console.log('Sending login request to:', `${config.URL}/account:login`);
      
      const response = await fetch(`${config.URL}/account:login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginPayload),
      });

      console.log('Login response status:', response.status);
      
      const data = await response.json();
      console.log('=== FULL LOGIN RESPONSE ===');
      console.log('Complete login response data:', JSON.stringify(data, null, 2));
      
      if (response.ok && data.LOGIN === "SUCCESSFUL") {
        console.log('Login successful for UID:', data.UID);
        
        // Clear Destiny chat session storage flags
        sessionStorage.removeItem('destinyChatDismissed');
        sessionStorage.removeItem('destinyChatCompleted');
        sessionStorage.removeItem('destinyUserHasChatted');
        
        // Extract email, phone, UID and notifications from login response
        const loginData = {
          uid: data.UID,
          email: data.EMAIL || data.email || email, // Use login response email or fallback to login email
          phone: data.PHONE || data.phone || '',
          newNotifications: data.NEW_NOTIFICATIONS || [],
          oldNotifications: data.OLD_NOTIFICATIONS || [],
          // Keep backward compatibility
          notifications: data.NOTIFICATIONS || []
        };
        
        console.log('Storing login data with email and phone:', loginData);
        
        // Use the onSuccessfulLogin handler with email and phone data
        await onSuccessfulLogin(data.UID, loginData);
        
      } else {
        console.error('Login failed:', data);
        if (data.LOGIN === "UNSUCCESSFUL" || data.ERROR !== "OK") {
          setError(data.MESSAGE || 'Invalid email or password');
        } else {
          setError('Login failed');
        }
      }
    } catch (error) {
      console.error('Login error:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4"
      style={{
        backgroundImage: assets.loginBackground ? `url(${assets.loginBackground})` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 opacity-70">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(139,92,246,0.1),transparent_50%)]"></div>
      </div>
      
      <Card className="relative z-10 w-full max-w-md">
        <CardHeader className="text-center space-y-6">
          <div className="relative mx-auto">
            <div className="absolute -inset-4 bg-gradient-to-r from-violet-500 to-purple-500 rounded-2xl blur opacity-20"></div>
            <div className="relative w-20 h-20 bg-white/10 backdrop-blur-xl rounded-2xl flex items-center justify-center shadow-2xl border border-white/20 overflow-hidden">
              {assets.logo ? (
                <img 
                  src={assets.logo} 
                  alt="Aligned Logo" 
                  className="w-18 h-18 object-cover scale-110"
                />
              ) : (
                <Heart className="w-8 h-8 text-white" />
              )}
            </div>
          </div>
          <div>
            <CardTitle className="text-4xl font-bold text-white mb-2 font-['Lavanderia']">
              Welcome to Aligned
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="email" className="text-sm font-medium text-white/90">
                Email Address
              </Label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-white/50" />
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-12"
                  required
                />
              </div>
            </div>

            <div className="space-y-3">
              <Label htmlFor="password" className="text-sm font-medium text-white/90">
                Password
              </Label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-white/50" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-12 pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/50 hover:text-white/80 transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-200 text-sm p-4 rounded-xl backdrop-blur-xl">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 text-base font-semibold"
            >
              {isLoading ? "Signing In..." : "Sign In"}
            </Button>

            <div className="text-center pt-4">
              <span className="text-white/60 font-medium">Don't have an account? </span>
              <Link 
                to="/register" 
                className="text-violet-300 hover:text-violet-200 font-semibold transition-colors hover:underline"
              >
                Sign up
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
