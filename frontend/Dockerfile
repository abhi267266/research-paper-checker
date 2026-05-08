FROM node:20-alpine AS base

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Environment variables must be present during build for Next.js
# But we can also use a standalone build or dev mode
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
