import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface AutocompleteInputProps {
  label: string;
  placeholder: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  required?: boolean;
  className?: string;
}

const AutocompleteInput = ({
  label,
  placeholder,
  options,
  value,
  onChange,
  disabled = false,
  required = false,
  className = ""
}: AutocompleteInputProps) => {
  const [inputValue, setInputValue] = useState(value);
  const [filteredOptions, setFilteredOptions] = useState<string[]>([]);
  const [showOptions, setShowOptions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const optionsRef = useRef<HTMLDivElement>(null);

  // Update input value when value prop changes
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Filter options based on input
  useEffect(() => {
    if (inputValue.trim() === "") {
      setFilteredOptions(options.slice(0, 10)); // Show first 10 options when empty
    } else {
      const filtered = options.filter(option =>
        option.toLowerCase().includes(inputValue.toLowerCase())
      );
      setFilteredOptions(filtered.slice(0, 10)); // Limit to 10 results
    }
    setHighlightedIndex(-1);
  }, [inputValue, options]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);
    setShowOptions(true);
    
    // If the input exactly matches an option, update the parent
    const exactMatch = options.find(option => 
      option.toLowerCase() === newValue.toLowerCase()
    );
    if (exactMatch) {
      onChange(exactMatch);
    } else {
      onChange(newValue);
    }
  };

  const handleOptionClick = (option: string) => {
    setInputValue(option);
    onChange(option);
    setShowOptions(false);
    inputRef.current?.blur();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showOptions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev < filteredOptions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev > 0 ? prev - 1 : filteredOptions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
          handleOptionClick(filteredOptions[highlightedIndex]);
        }
        break;
      case 'Escape':
        setShowOptions(false);
        setHighlightedIndex(-1);
        break;
    }
  };

  const handleFocus = () => {
    setShowOptions(true);
  };

  const handleBlur = (e: React.FocusEvent) => {
    // Delay hiding options to allow for option clicks
    setTimeout(() => {
      if (!optionsRef.current?.contains(e.relatedTarget as Node)) {
        setShowOptions(false);
      }
    }, 150);
  };

  return (
    <div className={cn("relative space-y-2", className)}>
      <Label htmlFor={label} className="text-sm font-medium text-white">
        {label} {required && "*"}
      </Label>
      <div className="relative">
        <Input
          ref={inputRef}
          id={label}
          value={inputValue}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="h-11 bg-white/10 backdrop-blur-sm border-white/30 text-white placeholder:text-white/60 focus:border-white/50"
          autoComplete="off"
        />
        
        {showOptions && filteredOptions.length > 0 && (
          <div
            ref={optionsRef}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-auto"
          >
            {filteredOptions.map((option, index) => (
              <div
                key={option}
                className={cn(
                  "px-3 py-2 cursor-pointer text-sm text-gray-900 hover:bg-violet-50",
                  highlightedIndex === index && "bg-violet-100"
                )}
                onClick={() => handleOptionClick(option)}
                onMouseEnter={() => setHighlightedIndex(index)}
              >
                {option}
              </div>
            ))}
            {filteredOptions.length === 0 && inputValue.trim() !== "" && (
              <div className="px-3 py-2 text-sm text-gray-500">
                No results found
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AutocompleteInput; 