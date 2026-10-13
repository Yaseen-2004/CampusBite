@echo off
cd /d "%~dp0frontend"
if not exist node_modules\vite\bin\vite.js npm install
npm run dev
