# =============================================================================
# Stage 1: Build the React SPA
# =============================================================================
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies using clean install
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source code and compile production bundles
COPY . .
RUN npm run build

# =============================================================================
# Stage 2: Serve static assets with Nginx
# =============================================================================
FROM nginx:alpine AS serve

# Copy compiled production bundle from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with reverse proxy and SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Container healthcheck
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
