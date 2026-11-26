import express from 'express';

import {
  getRazorpayKey,
  createOrder,
  verifyPayment,
  getAllPayments,
} from '../controllers/payment.controller.js';

const router = express.Router();

router.get('/get-key', getRazorpayKey);

router.post('/create-order', createOrder);

// In Live Mode we use this route as "webhook"
router.post('/verify', verifyPayment);

router.get('/all', getAllPayments);

export default router;