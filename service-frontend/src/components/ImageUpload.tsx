
import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Upload, X, Image as ImageIcon } from "lucide-react";
import { config } from "../config/api";

interface ImageUploadProps {
  images: File[];
  onImagesChange: (images: File[]) => void;
}

const ImageUpload = ({ images, onImagesChange }: ImageUploadProps) => {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFiles = (newFiles: File[]) => {
    const validFiles = newFiles.filter(file => 
      file.type.startsWith('image/') && images.length + newFiles.length <= config.MAX_IMAGES
    );
    
    if (validFiles.length > 0) {
      onImagesChange([...images, ...validFiles.slice(0, config.MAX_IMAGES - images.length)]);
    }
  };

  const removeImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index);
    onImagesChange(newImages);
  };

  const openFileDialog = () => {
    inputRef.current?.click();
  };

  return (
    <div className="space-y-4">
      <Label>Profile Pictures (Max {config.MAX_IMAGES})</Label>
      
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          dragActive ? 'border-orange-500 bg-orange-50' : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={(e) => e.target.files && handleFiles(Array.from(e.target.files))}
          className="hidden"
        />
        
        <div className="flex flex-col items-center space-y-2">
          <Upload className="h-8 w-8 text-gray-400" />
          <div className="text-sm text-gray-600">
            <span className="font-medium">Click to upload</span> or drag and drop
          </div>
          <div className="text-xs text-gray-400">
            PNG, JPG, GIF up to 10MB each
          </div>
          <Button type="button" variant="outline" onClick={openFileDialog}>
            Select Images
          </Button>
        </div>
      </div>

      {images.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {images.map((image, index) => (
            <Card key={index} className="relative p-2">
              <div className="aspect-square relative">
                <img
                  src={URL.createObjectURL(image)}
                  alt={`Preview ${index + 1}`}
                  className="w-full h-full object-cover rounded"
                />
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  className="absolute top-1 right-1 h-6 w-6 p-0"
                  onClick={() => removeImage(index)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
              <div className="text-xs text-gray-500 mt-1 truncate">
                {image.name}
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="text-sm text-gray-500">
        {images.length}/{config.MAX_IMAGES} images selected
      </div>
    </div>
  );
};

export default ImageUpload;
