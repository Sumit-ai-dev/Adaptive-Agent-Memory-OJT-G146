# Multi-stage production Dockerfile for AEMA React Frontend
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci || npm install

# Build static bundle with Vite
COPY . .
RUN npm run build

# Production web server stage
FROM nginx:alpine as runner

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx SPA & reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
