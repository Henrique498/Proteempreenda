const express = require('express');
const userController = require('../controllers/user.controller');
const { requireAuth } = require('../middlewares/auth');

const router = express.Router();

router.get('/me', requireAuth, userController.me);

module.exports = router;
