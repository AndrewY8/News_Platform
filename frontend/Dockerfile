# Use Node.js 18 as base
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies first (cache-friendly)
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy project files
COPY . .

# Install Tailwind + PostCSS (if not already in package.json)
RUN npm install -D tailwindcss postcss autoprefixer

# Build for production
RUN npm run build

# Runtime container
FROM node:18-alpine AS runner
WORKDIR /app

# Copy built output & node_modules
COPY --from=builder /app ./

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["npm", "start"]

