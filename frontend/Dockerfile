############################
# ---- Stage 1: Builder ----
############################
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Disable Next.js telemetry
ENV NEXT_TELEMETRY_DISABLED=1

# Copy dependency files
COPY package.json package-lock.json* ./

# Install all dependencies (including dev for build)
RUN npm ci --silent --legacy-peer-deps

# Copy source code
COPY . .

# Build the Next.js app
RUN npm run build

############################
# ---- Stage 2: Runtime ----
############################
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy only the built assets and required files
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json

# Install only production dependencies
RUN npm ci --omit=dev --silent --legacy-peer-deps

# Expose default Next.js port
EXPOSE 3000

# Default command
CMD ["npm", "start"]
