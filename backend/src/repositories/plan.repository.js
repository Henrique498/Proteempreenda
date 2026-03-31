const { getRequest } = require('../config/db');

async function listActivePlans() {
  const request = await getRequest();
  const result = await request.query(`
    SELECT Id, Slug, Nome, PrecoMensal, PrecoAnualTotal, Ativo
    FROM dbo.Plans
    WHERE Ativo = 1
    ORDER BY Id ASC
  `);

  return result.recordset;
}

async function findBySlug(slug) {
  const request = await getRequest();
  request.input('slug', slug);
  const result = await request.query(`
    SELECT TOP 1 Id, Slug, Nome, PrecoMensal, PrecoAnualTotal, Ativo
    FROM dbo.Plans
    WHERE Slug = @slug
  `);

  return result.recordset[0] || null;
}

module.exports = {
  listActivePlans,
  findBySlug
};
