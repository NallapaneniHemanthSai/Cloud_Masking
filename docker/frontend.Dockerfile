# Frontend image — PLACEHOLDER (Milestone 2 scaffold).
# The functional multi-stage build (Node build -> static serve) is authored in Milestone 17.

FROM node:20-alpine

WORKDIR /app

# NOTE: Do NOT build this image at Milestone 2. Real build steps added in M17 (after the Vite app in M14).
CMD ["node", "-e", "console.log('Cloud Masking frontend image is a Milestone 2 placeholder; built in M17.')"]
