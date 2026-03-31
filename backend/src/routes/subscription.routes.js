const express = require('express');
const subscriptionController = require('../controllers/subscription.controller');
const { requireAuth } = require('../middlewares/auth');

const router = express.Router();

router.get('/current', requireAuth, subscriptionController.current);
router.get('/mine', requireAuth, subscriptionController.listMine);
router.post('/checkout', requireAuth, subscriptionController.checkout);
router.patch('/:id/cancel', requireAuth, subscriptionController.cancel);

module.exports = router;
