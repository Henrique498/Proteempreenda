const subscriptionService = require('../services/subscription.service');
const {
  checkoutSchema,
  cancelSubscriptionParamsSchema
} = require('../validators/subscription.validator');

async function checkout(req, res, next) {
  try {
    const payload = checkoutSchema.parse(req.body);
    const result = await subscriptionService.checkout({
      userId: Number(req.user.sub),
      planSlug: payload.planSlug,
      billingCycle: payload.billingCycle,
      paymentMethod: payload.paymentMethod,
      cardLast4: payload.cardLast4
    });

    res.status(201).json(result);
  } catch (e) {
    if (e.name === 'ZodError') {
      return res.status(400).json({ error: true, message: 'Dados inválidos', details: e.issues });
    }
    return next(e);
  }
}

async function current(req, res, next) {
  try {
    const currentSubscription = await subscriptionService.getCurrent(Number(req.user.sub));
    res.json(currentSubscription);
  } catch (e) {
    next(e);
  }
}

async function listMine(req, res, next) {
  try {
    const subscriptions = await subscriptionService.listMySubscriptions(Number(req.user.sub));
    res.json(subscriptions);
  } catch (e) {
    next(e);
  }
}

async function cancel(req, res, next) {
  try {
    const params = cancelSubscriptionParamsSchema.parse(req.params);
    const canceled = await subscriptionService.cancelMySubscription(Number(req.user.sub), params.id);
    res.json(canceled);
  } catch (e) {
    if (e.name === 'ZodError') {
      return res.status(400).json({ error: true, message: 'Parâmetros inválidos', details: e.issues });
    }
    return next(e);
  }
}

module.exports = {
  checkout,
  current,
  listMine,
  cancel
};
