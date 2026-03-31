const express = require('express');
const paymentController = require('../controllers/payment.controller');
const { requireAuth } = require('../middlewares/auth');

const router = express.Router();

router.get('/mine', requireAuth, paymentController.listMine);

module.exports = router;
