import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { Heart, Check, X, Calendar as CalendarIcon, Eye, EyeOff, Clock, ChevronLeft, ChevronRight } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { config } from "../config/api";
import ImageUpload from "./ImageUpload";
import DateRoller from "./DateRoller";
import AutocompleteInput from "./AutocompleteInput";
import { countries, getCitiesForCountry } from "../data/locations";
import { useS3Assets } from "../hooks/useS3Assets";

const hobbiesOptions = [
  "Reading", "Traveling", "Cooking", "Sports", "Music", "Movies", 
  "Photography", "Dancing", "Fitness", "Gaming", "Art", "Gardening",
  "Writing", "Technology", "Fashion", "Yoga", "Swimming", "Hiking"
];

const steps = [
  { id: 1, title: "Basic Info", description: "Tell us about yourself" },
  { id: 2, title: "Location", description: "Where are you from?" },
  { id: 3, title: "Birth Details", description: "Your birth information" },
  { id: 4, title: "Interests", description: "What do you enjoy?" },
  { id: 5, title: "Photos", description: "Upload your pictures" },
  { id: 6, title: "Personal Questions", description: "Tell us more about yourself" }
];

const MultiStepRegister = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const { assets } = useS3Assets();
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    email: "",
    password: "",
    confirmPassword: "",
    city: "",
    country: "",
    profession: "",
    birth_city: "",
    birth_country: "",
    dob: null as Date | null,
    tob: "",
    gender: "",
    hobbies: [] as string[],
    question1Answer: "",
    question2Answer: "",
    question3Answer: "",
  });
  const [images, setImages] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [emailVerified, setEmailVerified] = useState(false);
  const [emailChecking, setEmailChecking] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleInputChange = (field: string, value: string | Date | null | string[]) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };
      
      if (field === 'country') {
        newData.city = "";
      }
      
      if (field === 'birth_country') {
        newData.birth_city = "";
      }
      
      return newData;
    });
  };

  const handleHobbyToggle = (hobby: string) => {
    setFormData(prev => ({
      ...prev,
      hobbies: prev.hobbies.includes(hobby)
        ? prev.hobbies.filter(h => h !== hobby)
        : [...prev.hobbies, hobby]
    }));
  };

  const handleEmailVerification = async (email: string) => {
    if (!email) return;
    
    setEmailChecking(true);
    try {
      const response = await fetch(`${config.URL}${config.ENDPOINTS.VERIFY_EMAIL}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();
      console.log('Email verification response:', data);
      
      if (response.ok) {
        // Updated logic to handle the actual response format
        if (data.verify === true) {
          setEmailVerified(true);
          setError('');
        } else if (data.verify === false) {
          setEmailVerified(false);
          setError(data.message || 'Email already exists. Please use a different email.');
        } else if (data.error) {
          setEmailVerified(false);
          setError(data.error);
        }
      } else {
        setEmailVerified(false);
        setError('Failed to verify email. Please try again.');
      }
    } catch (error) {
      console.error('Email verification error:', error);
      setEmailVerified(false);
      setError('Failed to verify email. Please try again.');
    } finally {
      setEmailChecking(false);
    }
  };

  const validateStep = (step: number) => {
    switch (step) {
      case 1:
        return formData.name && formData.phone && formData.email && formData.password && 
               formData.confirmPassword && emailVerified && formData.password === formData.confirmPassword;
      case 2:
        return formData.country && formData.city && formData.profession;
      case 3:
        return formData.birth_country && formData.birth_city && formData.dob && formData.tob && formData.gender;
      case 4:
        return formData.hobbies.length > 0;
      case 5:
        return images.length > 0;
      case 6:
        return formData.question1Answer.trim() && formData.question2Answer.trim() && formData.question3Answer.trim();
      default:
        return false;
    }
  };

  const nextStep = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, steps.length));
      setError("");
    } else {
      setError("Please fill in all required fields for this step.");
    }
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
    setError("");
  };

  const handleSubmit = async () => {
    if (!validateStep(6)) {
      setError('Please complete all required fields');
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const metadata = {
        name: formData.name,
        phone: formData.phone,
        email: formData.email,
        password: formData.password,
        city: formData.city,
        country: formData.country,
        profession: formData.profession,
        birth_city: formData.birth_city,
        birth_country: formData.birth_country,
        dob: formData.dob ? format(formData.dob, 'yyyy-MM-dd') : '',
        tob: formData.tob,
        gender: formData.gender,
        hobbies: formData.hobbies,
        Question1: {
          Question: "What does your ideal date look like?",
          Answer: formData.question1Answer
        },
        Question2: {
          Question: "What comforts you the most at the end of a tough day?",
          Answer: formData.question2Answer
        },
        Question3: {
          Question: "What kind of life do you imagine with your ideal partner?",
          Answer: formData.question3Answer
        }
      };

      const formDataToSend = new FormData();
      formDataToSend.append('metadata', JSON.stringify(metadata));
      
      images.forEach((image) => {
        formDataToSend.append('images', image);
      });

      console.log('Sending registration data to account:create endpoint:', metadata);

      const response = await fetch(`${config.URL}${config.ENDPOINTS.CREATE_ACCOUNT}`, {
        method: 'POST',
        body: formDataToSend,
      });

      const data = await response.json();
      console.log('Backend response:', data);
      
      if (response.ok) {
        navigate('/login');
      } else {
        setError(data.message || 'Registration failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
      console.error('Registration error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const passwordsMatch = formData.password && formData.confirmPassword && formData.password === formData.confirmPassword;
  const passwordsDontMatch = formData.password && formData.confirmPassword && formData.password !== formData.confirmPassword;

  const availableCities = formData.country ? getCitiesForCountry(formData.country) : [];
  const availableBirthCities = formData.birth_country ? getCitiesForCountry(formData.birth_country) : [];

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-sm font-medium text-white">Full Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  className="h-11 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone" className="text-sm font-medium text-white">Phone Number *</Label>
                <Input
                  id="phone"
                  value={formData.phone}
                  onChange={(e) => handleInputChange('phone', e.target.value)}
                  className="h-11 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-white">Email Address *</Label>
              <div className="relative">
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => {
                    handleInputChange('email', e.target.value);
                    if (e.target.value) {
                      handleEmailVerification(e.target.value);
                    }
                  }}
                  className="h-11 pr-10 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                  required
                />
                {emailChecking && (
                  <div className="absolute right-3 top-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  </div>
                )}
                {!emailChecking && formData.email && emailVerified && (
                  <Check className="absolute right-3 top-3 h-5 w-5 text-green-400" />
                )}
                {!emailChecking && formData.email && !emailVerified && (
                  <X className="absolute right-3 top-3 h-5 w-5 text-red-400" />
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium text-white">Password *</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    className="h-11 pr-10 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-white/70 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-sm font-medium text-white">Confirm Password *</Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    className="h-11 pr-10 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-3 text-white/70 hover:text-white"
                  >
                    {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                  {formData.confirmPassword && (
                    <div className="absolute right-12 top-3">
                      {passwordsMatch && <Check className="h-5 w-5 text-green-400" />}
                      {passwordsDontMatch && <X className="h-5 w-5 text-red-400" />}
                    </div>
                  )}
                </div>
                {passwordsDontMatch && (
                  <p className="text-sm text-red-400">Passwords do not match</p>
                )}
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <AutocompleteInput
                label="Country"
                placeholder="Type to search countries..."
                options={countries}
                value={formData.country}
                onChange={(value) => handleInputChange('country', value)}
                required={true}
              />

              <AutocompleteInput
                label="City"
                placeholder={formData.country ? "Type to search cities..." : "Select country first"}
                options={availableCities}
                value={formData.city}
                onChange={(value) => handleInputChange('city', value)}
                disabled={!formData.country}
                required={true}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="profession" className="text-sm font-medium text-white">Profession *</Label>
              <Input
                id="profession"
                value={formData.profession}
                onChange={(e) => handleInputChange('profession', e.target.value)}
                className="h-11 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                placeholder="e.g., Software Engineer, Doctor, Teacher"
                required
              />
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <AutocompleteInput
                label="Country of Birth"
                placeholder="Type to search countries..."
                options={countries}
                value={formData.birth_country}
                onChange={(value) => handleInputChange('birth_country', value)}
                required={true}
              />

              <AutocompleteInput
                label="City of Birth"
                placeholder={formData.birth_country ? "Type to search cities..." : "Select country first"}
                options={availableBirthCities}
                value={formData.birth_city}
                onChange={(value) => handleInputChange('birth_city', value)}
                disabled={!formData.birth_country}
                required={true}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-white">Date of Birth *</Label>
                <DateRoller
                  value={formData.dob}
                  onChange={(date) => handleInputChange('dob', date)}
                  placeholder="Pick a date"
                  className="h-11 bg-white/10 backdrop-blur-sm border-white/30 text-white hover:bg-white/20"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="tob" className="text-sm font-medium text-white">Time of Birth *</Label>
                <div className="relative">
                  <Input
                    id="tob"
                    type="time"
                    value={formData.tob}
                    onChange={(e) => handleInputChange('tob', e.target.value)}
                    className="h-11 pr-10 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
                    placeholder="14:30"
                    required
                  />
                  <Clock className="absolute right-3 top-3 h-5 w-5 text-violet-300 pointer-events-none" />
                </div>
                <p className="text-xs text-white/70">Format: 24-hour time (e.g., 14:30 for 2:30 PM)</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-white">Gender *</Label>
              <RadioGroup
                value={formData.gender}
                onValueChange={(value) => handleInputChange('gender', value)}
                className="flex flex-row space-x-6 mt-2"
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="male" id="male" className="border-white/30 text-white" />
                  <Label htmlFor="male" className="text-sm text-white">Male</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="female" id="female" className="border-white/30 text-white" />
                  <Label htmlFor="female" className="text-sm text-white">Female</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="other" id="other" className="border-white/30 text-white" />
                  <Label htmlFor="other" className="text-sm text-white">Other</Label>
                </div>
              </RadioGroup>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-white">Hobbies & Interests *</Label>
              <p className="text-sm text-white/70">Select up to 5 hobbies or interests</p>
              <div className="grid grid-cols-4 lg:grid-cols-5 gap-1.5 max-h-[300px] overflow-y-auto p-2">
                {hobbiesOptions.map((hobby) => (
                  <button
                    key={hobby}
                    type="button"
                    onClick={() => handleHobbyToggle(hobby)}
                    disabled={!formData.hobbies.includes(hobby) && formData.hobbies.length >= 5}
                    className={cn(
                      "group relative p-1.5 rounded-md text-left transition-all duration-200",
                      "border hover:border-violet-500/50",
                      "focus:outline-none focus:ring-1 focus:ring-violet-500 focus:ring-offset-1 focus:ring-offset-black",
                      formData.hobbies.includes(hobby)
                        ? "bg-gradient-to-br from-violet-500 to-purple-600 border-violet-500 text-white shadow-md shadow-violet-500/20"
                        : "bg-white/5 border-white/10 text-white/90 hover:bg-white/10",
                      !formData.hobbies.includes(hobby) && formData.hobbies.length >= 5 && "opacity-40 cursor-not-allowed hover:border-white/10 hover:bg-white/5"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-xs truncate">{hobby}</span>
                      {formData.hobbies.includes(hobby) && (
                        <div className="flex-shrink-0 ml-1">
                          <Check className="h-3 w-3" />
                        </div>
                      )}
                    </div>
                    <div className={cn(
                      "absolute inset-0 rounded-md transition-opacity duration-200",
                      formData.hobbies.includes(hobby)
                        ? "bg-gradient-to-br from-violet-500/20 to-purple-600/20 opacity-100"
                        : "bg-gradient-to-br from-violet-500/0 to-purple-600/0 opacity-0 group-hover:opacity-100"
                    )} />
                  </button>
                ))}
              </div>
              <div className="flex items-center justify-between mt-3 px-1">
                <p className="text-xs text-white/70">
                  Selected: {formData.hobbies.length}/5 hobbies
                </p>
                {formData.hobbies.length >= 5 && (
                  <span className="text-xs text-violet-300 font-medium">Maximum limit reached</span>
                )}
              </div>
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-6">
            <ImageUpload images={images} onImagesChange={setImages} />
          </div>
        );

      case 6:
        return (
          <div className="space-y-6">
            <div className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="question1" className="text-sm font-medium text-white">
                  What does your ideal date look like? *
                </Label>
                <Textarea
                  id="question1"
                  value={formData.question1Answer}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value.length <= 4000) {
                      handleInputChange('question1Answer', value);
                    }
                  }}
                  className="min-h-[120px] bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50 resize-none"
                  placeholder="Describe your ideal date experience..."
                  maxLength={4000}
                />
                <div className="flex justify-between text-xs text-white/70">
                  <span>Share your thoughts about the perfect romantic experience</span>
                  <span>{formData.question1Answer.length}/4000 characters</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="question2" className="text-sm font-medium text-white">
                  What comforts you the most at the end of a tough day? *
                </Label>
                <Textarea
                  id="question2"
                  value={formData.question2Answer}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value.length <= 4000) {
                      handleInputChange('question2Answer', value);
                    }
                  }}
                  className="min-h-[120px] bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50 resize-none"
                  placeholder="Tell us what brings you peace and comfort..."
                  maxLength={4000}
                />
                <div className="flex justify-between text-xs text-white/70">
                  <span>Help us understand what makes you feel at ease</span>
                  <span>{formData.question2Answer.length}/4000 characters</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="question3" className="text-sm font-medium text-white">
                  What kind of life do you imagine with your ideal partner? *
                </Label>
                <Textarea
                  id="question3"
                  value={formData.question3Answer}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (value.length <= 4000) {
                      handleInputChange('question3Answer', value);
                    }
                  }}
                  className="min-h-[120px] bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50 resize-none"
                  placeholder="Paint a picture of your future together..."
                  maxLength={4000}
                />
                <div className="flex justify-between text-xs text-white/70">
                  <span>Describe your vision of a shared future</span>
                  <span>{formData.question3Answer.length}/4000 characters</span>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div 
      className="min-h-screen bg-gradient-to-br from-purple-600 via-violet-600 to-purple-800 flex items-center justify-center p-4"
      style={{
        backgroundImage: assets.loginBackground ? `url(${assets.loginBackground})` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}
    >
      {/* Background overlay for better content readability */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-600 via-violet-600 to-purple-800 opacity-70"></div>
      <Card className="relative z-10 w-full max-w-4xl bg-white/10 backdrop-blur-md shadow-lg border-white/20">
        <CardHeader className="text-center space-y-4 px-6">
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
                <Heart className="w-6 h-6 text-white" />
              )}
            </div>
          </div>
          <div>
            <CardTitle className="text-2xl font-semibold text-white">
              Get Aligned
            </CardTitle>
            <CardDescription className="text-white/70 mt-2">
              Create your profile and find your soulmate
            </CardDescription>
          </div>
          
          {/* Progress indicator */}
          <div className="flex justify-center mt-6">
            <div className="flex items-center space-x-2">
              {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <div
                    className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                      currentStep >= step.id
                        ? "bg-gradient-to-r from-violet-500 to-purple-500 text-white"
                        : "bg-white/20 text-white/70"
                    )}
                  >
                    {currentStep > step.id ? <Check className="w-4 h-4" /> : step.id}
                  </div>
                  {index < steps.length - 1 && (
                    <div
                      className={cn(
                        "w-12 h-0.5 mx-2",
                        currentStep > step.id ? "bg-gradient-to-r from-violet-500 to-purple-500" : "bg-white/20"
                      )}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
          
          <div className="text-center">
            <h3 className="font-medium text-white">{steps[currentStep - 1].title}</h3>
            <p className="text-sm text-white/70">{steps[currentStep - 1].description}</p>
          </div>
        </CardHeader>
        
        <CardContent className="px-6">
          <div className="space-y-6">
            {renderStepContent()}

            {error && (
              <div className="text-red-300 text-sm text-center bg-red-500/20 p-3 rounded-md border border-red-300/30">
                {error}
              </div>
            )}

            {/* Navigation buttons */}
            <div className="flex justify-between pt-6">
              <Button
                type="button"
                variant="outline"
                onClick={prevStep}
                disabled={currentStep === 1}
                className="flex items-center gap-2 border-white/30 bg-white/10 text-white hover:bg-white/20"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </Button>

              {currentStep < steps.length ? (
                <Button
                  type="button"
                  onClick={nextStep}
                  disabled={!validateStep(currentStep)}
                  className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-purple-500 text-white hover:from-violet-600 hover:to-purple-600"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={handleSubmit}
                  disabled={isLoading || !validateStep(6)}
                  className="bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600 text-white font-medium"
                >
                  {isLoading ? "Creating Account..." : "Create Account"}
                </Button>
              )}
            </div>

            <div className="text-center pt-4">
              <span className="text-white/70">Already have an account? </span>
              <Link 
                to="/login" 
                className="text-violet-300 hover:text-violet-200 font-medium transition-colors"
              >
                Sign in
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MultiStepRegister;
