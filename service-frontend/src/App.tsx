
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import Index from "./pages/Index";
import { ChatProvider } from "./contexts/ChatContext";
import { ProfileProvider } from "./contexts/ProfileContext";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <ChatProvider>
        <ProfileProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <div className="w-full">
              <Index />
            </div>
          </BrowserRouter>
        </ProfileProvider>
      </ChatProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
