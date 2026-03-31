const express = require('express');
const planController = require('../controllers/plan.controller');

const router = express.Router();

router.get('/', planController.list);
router.get('/:slug', planController.getBySlug);

module.exports = router;
