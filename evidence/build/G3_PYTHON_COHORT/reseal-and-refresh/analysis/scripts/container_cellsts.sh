node --version
npm install --no-audit --no-fund --loglevel=error > /dev/null 2>&1; echo "npm install exit: $?"
echo "--- outputfiles/ before: $(ls -d outputfiles 2>&1 | head -1)"
echo "--- npm start (tsx index.ts), the repository's own entry point:"
npm start 2>&1 | tail -12
echo "npm start exit: ${PIPESTATUS[0]}"
echo "--- outputfiles/ after: $(ls outputfiles 2>&1 | head -3 | tr '\n' ' ')"
