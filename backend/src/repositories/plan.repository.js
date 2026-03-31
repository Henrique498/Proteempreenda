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

module.exports = {
  listActivePlans
};
