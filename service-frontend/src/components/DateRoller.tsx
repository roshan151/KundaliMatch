import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

interface DateRollerProps {
  value?: Date;
  onChange: (date: Date) => void;
  placeholder?: string;
  className?: string;
}

const RollerColumn: React.FC<{
  items: any[];
  selectedValue: any;
  onSelect: (value: any) => void;
  renderItem: (item: any) => string;
}> = ({ items, selectedValue, onSelect, renderItem }) => {
  return (
    <div className="h-48 overflow-y-auto scrollbar-hide">
      {items.map((item, index) => (
        <div
          key={index}
          onClick={() => onSelect(item)}
          className={cn(
            "px-2 py-1 cursor-pointer text-center transition-colors",
            selectedValue === item
              ? "bg-violet-600 text-white font-medium"
              : "text-gray-900 hover:bg-violet-100 hover:text-violet-900"
          )}
        >
          {renderItem(item)}
        </div>
      ))}
    </div>
  );
};

const DateRoller: React.FC<DateRollerProps> = ({ 
  value, 
  onChange, 
  placeholder = "Pick a date",
  className 
}) => {
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<number | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const days = Array.from({ length: 31 }, (_, i) => i + 1);
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 100 }, (_, i) => currentYear - i);

  useEffect(() => {
    if (value) {
      setSelectedDay(value.getDate());
      setSelectedMonth(value.getMonth());
      setSelectedYear(value.getFullYear());
    }
  }, [value]);

  const handleDateSelection = () => {
    if (selectedDay && selectedMonth !== null && selectedYear) {
      const newDate = new Date(selectedYear, selectedMonth, selectedDay);
      onChange(newDate);
      setIsOpen(false);
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const isDateSelected = selectedDay && selectedMonth !== null && selectedYear;

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "w-full justify-start text-left font-normal bg-white/10 border-white/20 text-white hover:bg-white/20",
            !value && "text-muted-foreground",
            isDateSelected && "border-violet-500",
            className
          )}
        >
          <Calendar className="mr-2 h-4 w-4 text-violet-300" />
          {value ? formatDate(value) : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0 z-50 bg-white/95 backdrop-blur-xl border-white/20" align="start">
        <div className="p-4">
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="text-center">
              <h4 className="text-sm font-medium mb-2 text-gray-900">Day</h4>
              <RollerColumn
                items={days}
                selectedValue={selectedDay}
                onSelect={setSelectedDay}
                renderItem={(day) => day.toString()}
              />
            </div>
            <div className="text-center">
              <h4 className="text-sm font-medium mb-2 text-gray-900">Month</h4>
              <RollerColumn
                items={months}
                selectedValue={selectedMonth !== null ? months[selectedMonth] : null}
                onSelect={(month) => setSelectedMonth(months.indexOf(month))}
                renderItem={(month) => month}
              />
            </div>
            <div className="text-center">
              <h4 className="text-sm font-medium mb-2 text-gray-900">Year</h4>
              <RollerColumn
                items={years}
                selectedValue={selectedYear}
                onSelect={setSelectedYear}
                renderItem={(year) => year.toString()}
              />
            </div>
          </div>
          <Button 
            onClick={handleDateSelection}
            className={cn(
              "w-full text-white",
              isDateSelected 
                ? "bg-violet-600 hover:bg-violet-700" 
                : "bg-gray-400 cursor-not-allowed"
            )}
            disabled={!isDateSelected}
          >
            {isDateSelected ? "Select Date" : "Select all fields"}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
};

export default DateRoller;
