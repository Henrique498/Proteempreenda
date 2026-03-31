const planService = require('../services/plan.service');

async function list(req, res, next) {
  try {
    const plans = await planService.listPlans();
    res.json(plans);
  } catch (e) {
    next(e);
  }
}

module.exports = {
  list
};
