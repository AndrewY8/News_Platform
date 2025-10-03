# Use Node.js 18
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Pre-compile Tailwind CSS to public folder (avoids PostCSS/Next.js conflict in Docker)
RUN npx tailwindcss -i ./app/globals.css -o ./public/styles.css --minify

ENV NODE_ENV=development
ENV PORT=3000

EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev"]
