const sql = require('mssql');
const env = require('./env');

let pool;

async function connectDb() {
  if (pool) return pool;
  if (env.db.connectionString) {
    pool = await sql.connect(env.db.connectionString);
    return pool;
  }
  const config = env.db.trustedConnection
    ? {
        server: env.db.server,
        database: env.db.database,
        port: env.db.port,
        driver: 'msnodesqlv8',
        options: {
          trustedConnection: true,
          encrypt: env.db.options.encrypt,
          trustServerCertificate: env.db.options.trustServerCertificate
        },
        pool: env.db.pool
      }
    : env.db;

  pool = await sql.connect(config);
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
