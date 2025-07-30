
import { useEffect, useState } from 'react';
import { toast } from "@/hooks/use-toast";
import { Bell } from "lucide-react";

interface Notification {
  message: string;
  updated: string;
  id?: string;
  seen?: boolean;
}

interface NotificationHandlerProps {
  notifications: Notification[];
  setHasNewNotifications?: (value: boolean) => void;
}

const NotificationHandler = ({ notifications, setHasNewNotifications }: NotificationHandlerProps) => {
  const [processedIds, setProcessedIds] = useState<string[]>([]);
  
  useEffect(() => {
    if (!notifications || notifications.length === 0) return;
    
    // Process only new notifications that haven't been shown yet
    const newNotifications = notifications.filter(notification => {
      // Create a unique ID if one doesn't exist
      const notificationId = notification.id || `${notification.message}-${notification.updated}`;
      return !processedIds.includes(notificationId);
    });
    
    if (newNotifications.length > 0) {
      // Update the hasNewNotifications flag if the setter is provided
      if (setHasNewNotifications) {
        setHasNewNotifications(true);
      }
      
      // Show toast notifications for each new notification
      newNotifications.forEach(notification => {
        const notificationId = notification.id || `${notification.message}-${notification.updated}`;
        
        toast({
          title: "New Notification",
          description: notification.message,
          variant: "default",
          duration: 5000,
        });
        
        // Add the notification ID to the processed list
        setProcessedIds(prev => [...prev, notificationId]);
      });
    }
  }, [notifications, processedIds, setHasNewNotifications]);

  return null; // This is a utility component that doesn't render anything
};

export default NotificationHandler;
