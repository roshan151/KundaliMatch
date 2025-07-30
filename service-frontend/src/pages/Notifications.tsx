import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Bell, User, Star } from "lucide-react";

interface User {
  uid: string;
  name: string;
  email?: string;
  city?: string;
  country?: string;
  age?: number;
  gender?: string;
  hobbies?: string | string[];
  profilePicture?: string;
  bio?: string;
  images?: string[];
  kundliScore?: number;
}

interface NotificationsProps {
  cachedData?: User[];
}

const Notifications = ({ cachedData }: NotificationsProps) => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<User[]>([]);

  useEffect(() => {
    if (cachedData) {
      setNotifications(cachedData);
    }
  }, [cachedData]);

  const handleBack = () => {
    navigate("/dashboard");
  };

  const UserCard = ({ user }: { user: User }) => (
    <Card className="group relative overflow-hidden bg-white/5 backdrop-blur-xl border border-white/10 hover:border-white/20 transition-all duration-500 hover:scale-[1.02] shadow-xl hover:shadow-2xl">
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
      <CardContent className="p-6 relative z-10">
        <div className="flex items-start space-x-4">
          <div className="relative">
            <Avatar className="w-24 h-24 ring-2 ring-white/20 group-hover:ring-white/40 transition-all duration-300">
              <AvatarImage 
                src={user.profilePicture} 
                className="object-cover w-full h-full"
              />
              <AvatarFallback className="bg-gradient-to-br from-blue-500 to-cyan-500 text-white font-semibold text-xl">
                {user.name?.charAt(0) || <User className="w-10 h-10" />}
              </AvatarFallback>
            </Avatar>
            <div className="absolute -inset-1 bg-gradient-to-br from-blue-400 to-cyan-400 rounded-full blur opacity-0 group-hover:opacity-30 transition-opacity duration-300"></div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg text-white/90 truncate group-hover:text-white transition-colors mb-1">
              {user.name || 'Unknown User'}
            </h3>
            {user.city && user.country && (
              <p className="text-sm text-white/60 truncate mb-1">
                📍 {user.city}, {user.country}
              </p>
            )}
            {user.age && (
              <p className="text-sm text-white/60 mb-1">
                🎂 {user.age} years old
              </p>
            )}
            {user.kundliScore !== undefined && (
              <div className="flex items-center mb-2">
                <Star className="w-4 h-4 text-yellow-400 mr-1" />
                <span className="text-sm text-white/70 font-medium">
                  Compatibility: {user.kundliScore}/36
                </span>
              </div>
            )}
            {user.hobbies && (
              <div className="space-y-2">
                <div className="flex flex-wrap gap-1.5">
                  {user.hobbies.split(',').slice(0, 3).map((hobby, index) => (
                    <Badge 
                      key={index} 
                      variant="secondary" 
                      className="text-xs bg-white/10 text-white/80 border-white/20 hover:bg-white/20 transition-colors px-2 py-1"
                    >
                      {hobby.trim()}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const EmptyState = () => (
    <div className="text-center py-20">
      <div className="relative mx-auto mb-6 w-20 h-20">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-full blur-xl"></div>
        <div className="relative w-20 h-20 bg-white/10 backdrop-blur-xl rounded-full flex items-center justify-center border border-white/20">
          <Bell className="w-8 h-8 text-white/60" />
        </div>
      </div>
      <h3 className="text-xl font-semibold text-white/90 mb-3">No notifications</h3>
      <p className="text-white/60 max-w-md mx-auto leading-relaxed">You're all caught up!</p>
    </div>
  );

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
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          
          <h1 className="text-xl font-semibold text-white amazon-font">
            Notifications
          </h1>
          
          <div className="w-24"></div>
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        <Card className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl overflow-hidden">
          <CardHeader className="pb-6 bg-gradient-to-r from-blue-500/10 to-cyan-500/10">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl blur opacity-30"></div>
                <div className="relative w-12 h-12 bg-white/10 backdrop-blur-xl rounded-xl border border-white/20 flex items-center justify-center">
                  <Bell className="w-6 h-6 text-blue-300" />
                </div>
              </div>
              <div>
                <CardTitle className="text-white text-xl font-bold">Notifications</CardTitle>
                <CardDescription className="text-white/60 font-medium mt-1">
                  Stay updated with your activity
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            {notifications.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {notifications.map((user) => (
                  <UserCard key={user.uid} user={user} />
                ))}
              </div>
            ) : (
              <EmptyState />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Notifications;
