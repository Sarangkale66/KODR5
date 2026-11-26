import "dotenv/config";
import express from "express";
import cookieParser from "cookie-parser";
import passport from "passport";
import path from "path";
import { fileURLToPath } from "url";

import { getGoogleStrategy } from "./oAuth/google.oAuth.js";
import { getDiscordStrategy } from "./oAuth/discord.oAuth.js";
import { signToken } from "./utils/jwt.js";
import { authenticateJWT } from "./middleware/auth.middleware.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

// 1. Core Middlewares
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, "public")));

// 2. Initialize Passport
app.use(passport.initialize());

// 3. Register Strategies
passport.use(getGoogleStrategy());
passport.use(getDiscordStrategy());

// 4. Google Auth Routes
app.get(
  "/auth/google",
  passport.authenticate("google", {
    session: false,
    scope: ["profile", "email"],
    prompt: "select_account"
  })
);

app.get(
  "/auth/google/callback",
  passport.authenticate("google", {
    failureRedirect: "/?error=google_failed",
    session: false
  }),
  (req, res) => {
    const token = signToken(req.user);
    res.cookie("token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 24 * 60 * 60 * 1000
    });
    return res.redirect("/dashboard");
  }
);

// 5. Discord Auth Routes
app.get(
  "/auth/discord",
  passport.authenticate("discord", { session: false })
);

app.get(
  "/auth/discord/callback",
  passport.authenticate("discord", {
    failureRedirect: "/?error=discord_failed",
    session: false
  }),
  (req, res) => {
    const token = signToken(req.user);
    res.cookie("token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 24 * 60 * 60 * 1000
    });
    return res.redirect("/dashboard");
  }
);

// 6. Protected UI & API Routes
app.get("/dashboard", authenticateJWT, (req, res) => {
  res.sendFile(path.join(__dirname, "public", "dashboard.html"));
});

app.get("/api/current-user", authenticateJWT, (req, res) => {
  res.json({ authenticated: true, user: req.user });
});

app.get("/auth/logout", (req, res) => {
  res.clearCookie("token");
  res.redirect("/");
});

app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// 7. Start Server
const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`🚀 Server running on: http://localhost:${port}`);
});

export default app;
