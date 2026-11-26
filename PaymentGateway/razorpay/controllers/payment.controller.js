import { validatePaymentVerification } from "razorpay/dist/utils/razorpay-utils.js";
import razorpayInstance from "../config/razorpay.js";
import Payment from "../models/payment.model.js";

export const getRazorpayKey = (req, res) => {
  res.status(200).json({
    success: true,
    key: process.env.RAZORPAY_KEY_ID,
  });
};

export const createOrder = async(req, res) => {
    try {
        const { amount } = req.body;
        const Amount = amount || 50;
        // test mode
        const options = {
        amount: Number(Amount) * 100, // Amount in paise
        currency: 'INR',
        receipt: `receipt_${Date.now()}`,
        };

        // razorPay request for order creation
        const order = await razorpayInstance.orders.create(options);

        await Payment.create({
            orderId: order.id,
            amount: Amount,
            currency: order.currency,
            status: 'pending',
        });

        res.status(200).json(order);
    } catch(err) {
        console.error('Error in createOrder:', err);
        res.status(500).json({
            success: false,
            message: 'Order create karne me error aaya',
            error: err.message,
        });
    }
}

export const verifyPayment = async(req, res) => {
    try {
        const { razorpayOrderId, razorpayPaymentId, signature } = req.body;
        const secret = process.env.RAZORPAY_KEY_SECRET;

        if (!razorpayOrderId || !razorpayPaymentId || !signature) {
            return res.status(400).json({
                success: false,
                message: 'Order ID, Payment ID ya Signature missing hai!',
            });
        }

        const isAuthentic = validatePaymentVerification(
            { order_id: razorpayOrderId, payment_id: razorpayPaymentId },
            signature,
            secret
        );

        if(isAuthentic) {
            const payment = await Payment.findOne({ orderId: razorpayOrderId });

            if (payment) {
                payment.paymentId = razorpayPaymentId;
                payment.signature = signature;
                payment.status = 'completed';
                await payment.save();
            }

            return res.status(200).json({
                success: true,
                message: 'Payment verified successfully! 🎉',
            });
        } else {
            await Payment.findOneAndUpdate(
                { orderId: razorpayOrderId },
                { status: 'failed' }
            );

            return res.status(400).json({
                success: false,
                message: 'Invalid signature! Payment fake ya tampered ho sakti hai.',
            });
        }


    } catch(err) {
        console.error('Error in verifyPayment:', err);
            res.status(500).json({
            success: false,
            message: 'Payment verification ke waqt error aaya',
            error: err.message,
        });
    }
};


export const getAllPayments = async (req, res) => {
  try {
    const payments = await Payment.find().sort({ createdAt: -1 });
    res.status(200).json({
      success: true,
      count: payments.length,
      data: payments,
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};