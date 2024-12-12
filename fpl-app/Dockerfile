# Use an official Node.js image to build the React app
FROM node:18 AS build

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the app for production
RUN npm run build

# Step 2: Set up Nginx to serve the build files
FROM nginx:alpine AS production-stage

# Copy the build files from the build stage to Nginx's default folder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 for Nginx
EXPOSE 80

# Run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]