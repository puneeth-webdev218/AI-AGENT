import express from 'express';
import cors from 'cors';
import { serverConfig } from './config/oauth.js';
import { googleAuthRouter } from './routes/googleAuthRoutes.js';
import { emailRouter } from './routes/emailRoutes.js';

const app = express();

app.use(cors({ origin: serverConfig.allowedOrigin, credentials: true }));
app.use(express.json());

app.use(googleAuthRouter);
app.use(emailRouter);

app.listen(serverConfig.port, () => {
  console.log(`[email] Gmail OAuth backend listening on http://localhost:${serverConfig.port}`);
});
