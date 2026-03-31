const sql = require('mssql');
const env = require('./env');

let pool;

async function connectDb() {
  if (pool) return pool;
  pool = await sql.connect(env.db);
  return pool;
}

async function getRequest() {
  const p = await connectDb();
  return p.request();
}

module.exports = {
  sql,
  connectDb,
  getRequest
};
