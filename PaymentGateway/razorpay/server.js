import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import connectDB from './config/db.js';
import paymentRoutes from './routes/payment.routes.js';
connectDB();

const dirname = path.dirname(fileURLToPath(import.meta.url))

const app = express();

app.use(cors())
app.use(express.json())
app.use(express.urlencoded({ extended:true }))
app.use(express.static(path.join(dirname, "public")))


app.use('/api/payment', paymentRoutes);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Razorpay Server ready at: http://localhost:${PORT}`);
});