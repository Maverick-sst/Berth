FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine
# Upgrade base OS packages at build time: the base image freezes packages at
# its build date, so fresh HIGH/CRITICAL fixes land only via apk upgrade here.
USER 0
RUN apk update && apk upgrade --no-cache && apk cache clean || true
USER 101
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
