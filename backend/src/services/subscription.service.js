const planRepository = require('../repositories/plan.repository');
const paymentRepository = require('../repositories/payment.repository');
const subscriptionRepository = require('../repositories/subscription.repository');

const FREE_TRIAL_DAYS = 30;

function getPaymentStatus(paymentMethod) {
  if (paymentMethod === 'pix') return 'paid';
  if (paymentMethod === 'manual') return 'paid';
  return 'pending';
}

function getPlanPrice(plan, billingCycle) {
  return billingCycle === 'anual' ? Number(plan.PrecoAnualTotal) : Number(plan.PrecoMensal);
}

function isFreePlan(plan) {
  const mensal = Number(plan.PrecoMensal || 0);
  const anual = Number(plan.PrecoAnualTotal || 0);
  const slug = String(plan.Slug || '').toLowerCase();
  return (mensal <= 0 && anual <= 0) || slug === 'gratuito' || slug === 'free';
}

function mapPlan(plan) {
  return {
    Id: plan.Id,
    Slug: plan.Slug,
    Nome: plan.Nome,
    PrecoMensal: Number(plan.PrecoMensal),
    PrecoAnualTotal: Number(plan.PrecoAnualTotal)
  };
}

async function getPaidPlanOptions() {
  const plans = await planRepository.listActivePlans();
  return plans
    .filter((p) => Number(p.PrecoMensal || 0) > 0 || Number(p.PrecoAnualTotal || 0) > 0)
    .slice(0, 3)
    .map(mapPlan);
}

async function checkout({ userId, planSlug, billingCycle, paymentMethod, cardLast4 }) {
  const plan = await planRepository.findBySlug(planSlug);
  if (!plan || !plan.Ativo) {
    const err = new Error('Plano inválido ou inativo');
    err.status = 404;
    throw err;
  }

  await subscriptionRepository.cancelActiveByUserId(userId);

  if (isFreePlan(plan)) {
    const alreadyUsedFreeTrial = await subscriptionRepository.hasSubscriptionHistoryByUserAndPlan(
      userId,
      plan.Id
    );

    if (alreadyUsedFreeTrial) {
      const err = new Error('Período gratuito já utilizado. Escolha uma das 3 assinaturas pagas.');
      err.status = 403;
      err.code = 'FREE_TRIAL_ALREADY_USED';
      err.paidPlans = await getPaidPlanOptions();
      throw err;
    }

    const subscription = await subscriptionRepository.createTrialSubscription({
      userId,
      planId: plan.Id,
      trialDays: FREE_TRIAL_DAYS
    });

    return {
      subscription,
      payment: null,
      plan: mapPlan(plan),
      isTrial: true,
      trialDays: FREE_TRIAL_DAYS,
      trialEndsAt: subscription.EndAt,
      message: 'Plano gratuito ativado por 30 dias. Após esse período, escolha uma assinatura paga.'
    };
  }

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
    plan: mapPlan(plan),
    isTrial: false
  };
}

async function getCurrent(userId) {
  await subscriptionRepository.markEndedAsExpiredByUserId(userId);
  const current = await subscriptionRepository.getCurrentByUserId(userId);
  if (current) return current;

  const hasUsedFreeTrial = await subscriptionRepository.hasUsedAnyFreeTrialByUserId(userId);
  if (!hasUsedFreeTrial) return null;

  const paidPlans = await getPaidPlanOptions();
  if (!paidPlans.length) return null;

  return {
    subscription: null,
    upgradeRequired: true,
    message: 'Seu período gratuito terminou. Escolha uma das 3 assinaturas pagas.',
    paidPlans
  };
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
