@echo off

npx webpack --config webpack.config.js --mode=development && python -m uvicorn main:app --reload