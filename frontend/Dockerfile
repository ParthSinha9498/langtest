# Production-ish image: build once, serve the static bundle with nginx. This
# is what docker-compose's `frontend` service builds. For local dev with hot
# reload, `make frontend` runs the plain node:20-alpine image directly
# against a bind-mounted ./frontend instead — no separate Dockerfile needed
# for that since it's just `npm run dev` against live source.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8010
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
