FROM nginx:1.28-alpine

# yq converts the selected language YAML into the runtime JS dictionary at boot.
RUN apk add --no-cache yq

COPY ui/index.html /usr/share/nginx/html/index.html
COPY ui/styles.css /usr/share/nginx/html/styles.css
COPY ui/app.js /usr/share/nginx/html/app.js
COPY ui/i18n.js /usr/share/nginx/html/i18n.js
COPY ui/locales /usr/share/nginx/html/locales
COPY ui/assets /usr/share/nginx/html/assets

# Renders /usr/share/nginx/html/i18n-active.js from UI_LANG before nginx starts.
COPY ui/docker-entrypoint.d/40-render-i18n.sh /docker-entrypoint.d/40-render-i18n.sh
RUN chmod +x /docker-entrypoint.d/40-render-i18n.sh
