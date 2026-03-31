const { getRequest, sql } = require('../config/db');

async function findByEmail(email) {
  const request = await getRequest();
  request.input('email', sql.NVarChar(200), email);
  const result = await request.query(`
    SELECT TOP 1 Id, Nome, Email, SenhaHash, Tipo, Ativo
    FROM dbo.Users
    WHERE Email = @email
  `);
  return result.recordset[0] || null;
}

async function createUser({ nome, email, senhaHash, tipo }) {
  const request = await getRequest();
  request.input('nome', sql.NVarChar(150), nome);
  request.input('email', sql.NVarChar(200), email);
  request.input('senhaHash', sql.NVarChar(255), senhaHash);
  request.input('tipo', sql.NVarChar(20), tipo);

  const result = await request.query(`
    INSERT INTO dbo.Users (Nome, Email, SenhaHash, Tipo)
    OUTPUT INSERTED.Id, INSERTED.Nome, INSERTED.Email, INSERTED.Tipo
    VALUES (@nome, @email, @senhaHash, @tipo)
  `);

  return result.recordset[0];
}

module.exports = {
  findByEmail,
  createUser
};
