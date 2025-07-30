import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { S3_CONFIG } from "../config/s3";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Initialize S3 client
const s3Client = new S3Client({
  region: S3_CONFIG.REGION,
  credentials: {
    accessKeyId: S3_CONFIG.ACCESS_ID,
    secretAccessKey: S3_CONFIG.ACCESS_KEY
  }
});

// Function to get signed URL for an S3 object
export const getSignedS3Url = async (key: string) => {
  try {
    const command = new GetObjectCommand({
      Bucket: S3_CONFIG.BUCKET,
      Key: key
    });
    const signedUrl = await getSignedUrl(s3Client, command, { expiresIn: 3600 }); // URL expires in 1 hour
    return signedUrl;
  } catch (error) {
    console.error('Error generating signed URL:', error);
    return null;
  }
};

// Function to extract key from S3 URL
export const extractS3Key = (url: string) => {
  const match = url.match(/amazonaws\.com\/(.+)/);
  return match ? match[1] : null;
};
