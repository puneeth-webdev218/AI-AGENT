import dotenv from 'dotenv';

dotenv.config();

export const oauthConfig = {
  clientId: process.env.CLIENT_ID || '',
  clientSecret: process.env.CLIENT_SECRET || '',
  redirectUri: process.env.REDIRECT_URI || 'http://localhost:8000/auth/google/callback',
  scope: 'https://www.googleapis.com/auth/gmail.readonly',
};

export const serverConfig = {
  port: Number(process.env.PORT || 8001),
  allowedOrigin: process.env.ALLOWED_ORIGIN || 'http://localhost:5173',
};
