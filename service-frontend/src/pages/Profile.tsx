import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Profile from "../components/Profile";
import EditProfile from "../components/EditProfile";
import { Button } from "@/components/ui/button";
import { ArrowLeft, LogOut, Edit, RefreshCw } from "lucide-react";

interface ProfileData {
  uid: string;
  email: string;
  name: string;
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
  Question1?: { Question: string; Answer: string };
  Question2?: { Question: string; Answer: string };
  Question3?: { Question: string; Answer: string };
}

interface ProfilePageProps {
  cachedProfileData?: ProfileData | null;
  isLoadingProfile?: boolean;
  onLogout?: () => void;
}

const ProfilePage = ({ cachedProfileData, isLoadingProfile, onLogout }: ProfilePageProps) => {
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);

  const handleBack = () => {
    navigate("/dashboard");
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleSaveEdit = () => {
    setIsEditing(false);
  };

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    } else {
      // Fallback to old behavior
      localStorage.removeItem('userUID');
      localStorage.removeItem('userData');
      localStorage.removeItem('profileData');
      localStorage.removeItem('dashboardData');
    }
    
    // Force a complete page reload to reset the app state
    window.location.href = "/login";
  };

  const handleUpdate = () => {
    // Refresh the page to update profile data
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(139,92,246,0.1),transparent_50%)]"></div>
      
      {/* Header */}
      <div className="relative z-10 border-b border-white/10 bg-white/5 backdrop-blur-2xl sticky top-0">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
          <Button 
            onClick={handleBack}
            variant="ghost" 
            className="text-white/80 hover:text-white hover:bg-white/10"
          >
            <ArrowLeft className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Back to Dashboard</span>
          </Button>
          
          <h1 className="text-xl font-semibold text-white amazon-font">
            <span className="hidden sm:inline">
              {isEditing ? 'Edit Profile' : 'My Profile'}
            </span>
            <span className="sm:hidden">
              {isEditing ? 'Edit Profile' : ''}
            </span>
          </h1>
          
          <div className="flex gap-2">
            <Button 
              onClick={handleLogout}
              variant="outline"
              className="border-red-400/30 bg-red-500/10 text-red-200 hover:bg-red-500/20"
            >
              <LogOut className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Logout</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Profile Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        {isEditing ? (
          <EditProfile onCancel={handleCancelEdit} onSave={handleSaveEdit} />
        ) : (
          <Profile 
            onEdit={handleEdit} 
            cachedProfileData={cachedProfileData}
            isLoadingProfile={isLoadingProfile}
          />
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
