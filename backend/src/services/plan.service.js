const planRepository = require('../repositories/plan.repository');

async function listPlans() {
  return planRepository.listActivePlans();
}

async function getPlanBySlug(slug) {
  const plan = await planRepository.findBySlug(slug);
  if (!plan || !plan.Ativo) {
    const err = new Error('Plano não encontrado');
    err.status = 404;
    throw err;
  }

  return plan;
}

module.exports = {
  listPlans,
  getPlanBySlug
};
