const planRepository = require('../repositories/plan.repository');

async function listPlans() {
  return planRepository.listActivePlans();
}

module.exports = {
  listPlans
};
