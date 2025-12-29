FROM node:22-alpine

WORKDIR /app

# Accept build arg for API base URL
ARG PUBLIC_API_BASE_URL=http://localhost:8000

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source
COPY . .

# Set environment variable for build (Vite bakes these in at build time)
ENV VITE_API_BASE=${PUBLIC_API_BASE_URL}
ENV PUBLIC_API_BASE_URL=${PUBLIC_API_BASE_URL}
ENV ADAPTER=node

# Generate SvelteKit configuration and build for production
RUN npm run prepare
RUN npm run build

EXPOSE 3000

ENV HOST=0.0.0.0
ENV PORT=3000

# Run the built production server
CMD ["node", "build"]
