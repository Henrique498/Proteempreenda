const paymentService = require('../services/payment.service');

async function listMine(req, res, next) {
  try {
    const payments = await paymentService.listMyPayments(Number(req.user.sub));
    res.json(payments);
  } catch (e) {
    next(e);
  }
}

module.exports = {
  listMine
};
