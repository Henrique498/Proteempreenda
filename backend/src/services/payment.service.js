const paymentRepository = require('../repositories/payment.repository');

async function listMyPayments(userId) {
  return paymentRepository.listByUserId(userId);
}

module.exports = {
  listMyPayments
};
