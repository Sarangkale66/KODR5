import express from "express";
import env from "./config/env.js"
import morgan from "morgan"
import securityMiddleware from "./middleware/security.middleware.js";
import notFound from "./middleware/notFound.middleware.js";
import errorHandlerMiddleware from "./middleware/errorHandler.middleware.js";

export default function createApp() {
    const app = express();

    if(env.NODE_ENV === 'development') 
        app.use(morgan("dev"));

    app.get("/health", (req, res)=> {
        throw new Error("meko pasad nahi aaya")
    })

    securityMiddleware(app);
    app.use(notFound);
    app.use(errorHandlerMiddleware);

    return app;
}