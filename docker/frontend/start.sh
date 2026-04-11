#!/bin/sh
set -e

cd /app/frontend

if [ ! -d node_modules ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  npm install
fi

npm run dev -- --host 0.0.0.0 --port 5173
