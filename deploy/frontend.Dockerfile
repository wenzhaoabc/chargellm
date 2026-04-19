FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY frontend ./

RUN if [ -f /app/package-lock.json ] || [ -f /app/npm-shrinkwrap.json ]; then npm ci; \
    elif [ -f /app/package.json ]; then npm install; \
    else echo "Missing /app/package.json" && exit 1; fi

RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
