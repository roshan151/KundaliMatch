# Build stage
FROM node:20-alpine AS build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all files
COPY . .

RUN npm install --save-dev terser

# Set production environment variables for build
ENV VITE_API_URL=/api
ENV VITE_PROFILE_API_URL=/api

# Build the application with production API URLs
ENV VITE_API_URL=/api
ENV VITE_PROFILE_API_URL=/api
ENV NODE_ENV=production
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8080
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]