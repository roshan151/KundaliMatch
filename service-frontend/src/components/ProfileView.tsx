import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from "@/components/ui/carousel";
import { User, MapPin, Calendar, ArrowLeft, Camera, Star } from "lucide-react";
import { User as UserType } from "../types";

interface ProfileViewProps {
  user: UserType;
  onBack: () => void;
  children?: React.ReactNode;
}

const ProfileView = ({ user, onBack, children }: ProfileViewProps) => {
  // Helper function to safely get hobbies array
  const getHobbiesArray = (hobbies: string | string[] | undefined): string[] => {
    if (!hobbies) return [];
    if (Array.isArray(hobbies)) return hobbies;
    if (typeof hobbies === 'string') {
      return hobbies.split(',').map(hobby => hobby.trim()).filter(hobby => hobby.length > 0);
    }
    return [];
  };

  const hobbiesArray = getHobbiesArray(user.hobbies);

  return (
    <div className="w-full max-w-2xl mx-auto overflow-x-hidden">
      <Button 
        onClick={onBack}
        variant="ghost" 
        className="mb-6 text-white/70 hover:text-white hover:bg-white/10"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back
      </Button>
      
      <Card className="overflow-hidden">
        <CardContent className="p-8">
          <div className="text-center mb-8">
            <div className="relative mx-auto mb-6">
              <div className="absolute -inset-2 bg-gradient-to-r from-violet-500 to-purple-500 rounded-full blur opacity-30"></div>
              <Avatar className="relative w-32 h-32 ring-4 ring-white/20 shadow-2xl">
                <AvatarImage src={user.profilePicture || (user.images && user.images.length > 0 ? user.images[0] : undefined)} />
                <AvatarFallback className="bg-gradient-to-r from-violet-500 to-purple-500 text-white text-2xl font-bold">
                  {user.name?.charAt(0) || <User className="w-12 h-12" />}
                </AvatarFallback>
              </Avatar>
            </div>
            
            <h1 className="text-3xl font-bold text-white mb-4">
              {user.name || 'Unknown User'}
            </h1>
            
            <div className="flex items-center justify-center flex-wrap gap-3 text-white/70 mb-6">
              {user.age && (
                <div className="flex items-center bg-white/10 backdrop-blur-xl rounded-full px-4 py-2 border border-white/20">
                  <Calendar className="w-4 h-4 mr-2" />
                  <span className="font-medium">{user.age} years old</span>
                </div>
              )}
              {user.city && user.country && (
                <div className="flex items-center bg-white/10 backdrop-blur-xl rounded-full px-4 py-2 border border-white/20">
                  <MapPin className="w-4 h-4 mr-2" />
                  <span className="font-medium">{user.city}, {user.country}</span>
                </div>
              )}
              {user.kundliScore !== undefined && (
                <div className="flex items-center bg-gradient-to-r from-yellow-500/20 to-orange-500/20 backdrop-blur-xl rounded-full px-4 py-2 border border-yellow-500/30">
                  <Star className="w-4 h-4 mr-2 text-yellow-400" />
                  <span className="font-medium text-yellow-200">Compatibility: {user.kundliScore}/36</span>
                </div>
              )}
            </div>
          </div>

          {user.bio && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-white mb-3">About</h3>
              <div className="bg-white/5 backdrop-blur-xl rounded-xl p-6 border border-white/10">
                <p className="text-white/80 leading-relaxed font-medium">
                  {user.bio}
                </p>
              </div>
            </div>
          )}

          {hobbiesArray.length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-white mb-4">Interests</h3>
              <div className="flex flex-wrap gap-2">
                {hobbiesArray.map((hobby, index) => (
                  <Badge key={`hobby-${user.uid}-${index}`} variant="secondary" className="bg-white/10 text-white/90 hover:bg-white/20 border border-white/20 px-3 py-1">
                    {hobby}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {user.images && user.images.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Camera className="w-5 h-5 text-white" />
                <h3 className="text-lg font-semibold text-white">Photos</h3>
              </div>
              <div className="relative px-12">
                <Carousel className="w-full max-w-md mx-auto">
                  <CarouselContent>
                    {user.images.map((image, index) => (
                      <CarouselItem key={`image-${user.uid}-${index}`}>
                        <div className="relative aspect-[3/4] overflow-hidden rounded-xl bg-white/5 backdrop-blur-xl border border-white/10">
                          <img
                            src={image}
                            alt={`Photo ${index + 1} of ${user.name}`}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              console.error('Failed to load image:', image);
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                        </div>
                      </CarouselItem>
                    ))}
                  </CarouselContent>
                  {user.images.length > 1 && (
                    <>
                      <CarouselPrevious className="bg-white/10 backdrop-blur-xl border-white/20 text-white hover:bg-white/20 -left-12" />
                      <CarouselNext className="bg-white/10 backdrop-blur-xl border-white/20 text-white hover:bg-white/20 -right-12" />
                    </>
                  )}
                </Carousel>
              </div>
            </div>
          )}

          {children && (
            <div className="border-t border-white/10 pt-6">
              {children}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ProfileView;
