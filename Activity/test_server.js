const http = require("http");
const crypto = require("crypto");

const PORT = 3000;
const HOST = "0.0.0.0";

let requestCount = 0;

const server = http.createServer((req, res) => {
  requestCount++;

  // Real-world CPU work (Auth/Bcrypt/Database simulation)
  if (req.url.includes("heavy") || req.url.includes("api") || req.url === "/") {
    // Light cryptographic hash to simulate real backend processing
    crypto.pbkdf2Sync("student_password", "salt_token", 3000, 32, "sha512");
  }

  const data = {
    message: "Student Backend API Response",
    status: "online",
    instance: "student-01",
    requestId: requestCount,
    timestamp: new Date().toISOString()
  };

  res.writeHead(200, {
    "Content-Type": "application/json",
    "Connection": "keep-alive"
  });
  res.end(JSON.stringify(data));
});

server.listen(PORT, HOST, () => {
  console.log(`Node.js server listening on http://${HOST}:${PORT}`);
});
