const planService = require('../services/plan.service');

async function list(req, res, next) {
  try {
    const plans = await planService.listPlans();
    res.json(plans);
  } catch (e) {
    next(e);
  }
}

async function getBySlug(req, res, next) {
  try {
    const plan = await planService.getPlanBySlug(req.params.slug);
    res.json(plan);
  } catch (e) {
    next(e);
  }
}

module.exports = {
  list,
  getBySlug
};
