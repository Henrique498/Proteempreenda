const planRepository = require('../repositories/plan.repository');
const paymentRepository = require('../repositories/payment.repository');
const subscriptionRepository = require('../repositories/subscription.repository');

function getPaymentStatus(paymentMethod) {
  if (paymentMethod === 'pix') return 'paid';
  if (paymentMethod === 'manual') return 'paid';
  return 'pending';
}

function getPlanPrice(plan, billingCycle) {
  return billingCycle === 'anual' ? Number(plan.PrecoAnualTotal) : Number(plan.PrecoMensal);
}

async function checkout({ userId, planSlug, billingCycle, paymentMethod, cardLast4 }) {
  const plan = await planRepository.findBySlug(planSlug);
  if (!plan || !plan.Ativo) {
    const err = new Error('Plano inválido ou inativo');
    err.status = 404;
    throw err;
  }

  await subscriptionRepository.cancelActiveByUserId(userId);

  const subscription = await subscriptionRepository.createSubscription({
    userId,
    planId: plan.Id,
    billingCycle,
    status: 'active'
  });

  const amount = getPlanPrice(plan, billingCycle);
  const paymentStatus = getPaymentStatus(paymentMethod);

  const payment = await paymentRepository.createPayment({
    subscriptionId: subscription.Id,
    userId,
    planId: plan.Id,
    provider: paymentMethod,
    providerPaymentId: null,
    valor: amount,
    currency: 'BRL',
    status: paymentStatus,
    metadataJson: JSON.stringify({ billingCycle, cardLast4: cardLast4 || null })
  });

  return {
    subscription,
    payment,
    plan: {
      Id: plan.Id,
      Slug: plan.Slug,
      Nome: plan.Nome,
      PrecoMensal: Number(plan.PrecoMensal),
      PrecoAnualTotal: Number(plan.PrecoAnualTotal)
    }
  };
}

async function getCurrent(userId) {
  return subscriptionRepository.getCurrentByUserId(userId);
}

async function listMySubscriptions(userId) {
  return subscriptionRepository.listByUserId(userId);
}

async function cancelMySubscription(userId, subscriptionId) {
  const updated = await subscriptionRepository.cancelByIdForUser(subscriptionId, userId);
  if (!updated) {
    const err = new Error('Assinatura não encontrada');
    err.status = 404;
    throw err;
  }

  return updated;
}

module.exports = {
  checkout,
  getCurrent,
  listMySubscriptions,
  cancelMySubscription
};
