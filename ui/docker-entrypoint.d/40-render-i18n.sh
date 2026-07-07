#!/bin/sh
# Renders the language dictionary the browser loads, from the YAML file selected
# by the UI_LANG environment variable. Runs automatically before nginx starts
# (the official nginx image executes /docker-entrypoint.d/*.sh on boot), so the
# language can be switched per deploy without rebuilding the image.
set -eu

ROOT="/usr/share/nginx/html"
LANG_CODE="${UI_LANG:-en}"
SRC="${ROOT}/locales/${LANG_CODE}.yaml"

if [ ! -f "$SRC" ]; then
  echo "[i18n] UI_LANG=${LANG_CODE} has no locales/${LANG_CODE}.yaml; falling back to en" >&2
  LANG_CODE="en"
  SRC="${ROOT}/locales/en.yaml"
fi

OUT="${ROOT}/i18n-active.js"
{
  echo "// Generated at container start from locales/${LANG_CODE}.yaml (UI_LANG=${UI_LANG:-en}). Do not edit."
  echo "window.APP_CONFIG = window.APP_CONFIG || {};"
  echo "window.APP_CONFIG.lang = \"${LANG_CODE}\";"
  printf 'window.I18N_MESSAGES = '
  yq -o=json '.' "$SRC"
  echo ";"
} > "$OUT"

echo "[i18n] rendered ${OUT} for language ${LANG_CODE}"
