import "dotenv/config"
import express from "express"
import { fileURLToPath } from "url"
import path from "path"
import http from "http"
import { setupSocketServer } from "./socket/socket.js"

const app = express();
const httpServer = http.createServer(app);
const PORT = process.env.PORT || 3000;

const __filename = path.dirname(fileURLToPath(import.meta.url));
app.use(express.static(path.join( __filename, "public")))
setupSocketServer(httpServer)

httpServer.listen(PORT,()=>{
    console.log("server running on port:", PORT);
})