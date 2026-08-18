# Build the static bundle, then serve it through nginx with an API reverse proxy.
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

ARG VITE_API_BASE_URL=/api
ARG VITE_API_DOCS_URL=/docs
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_API_DOCS_URL=$VITE_API_DOCS_URL

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 3000
