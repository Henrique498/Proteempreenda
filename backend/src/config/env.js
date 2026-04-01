const dotenv = require('dotenv');

dotenv.config();

module.exports = {
  port: Number(process.env.PORT || 3001),
  nodeEnv: process.env.NODE_ENV || 'development',
  jwtSecret: process.env.JWT_SECRET || 'dev-secret',
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || '8h',
  db: {
    connectionString: process.env.DB_CONNECTION_STRING || '',
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    server: process.env.DB_SERVER,
    port: Number(process.env.DB_PORT || 1433),
    database: process.env.DB_NAME,
    trustedConnection: String(process.env.DB_TRUSTED || 'false') === 'true',
    options: {
      encrypt: String(process.env.DB_ENCRYPT || 'false') === 'true',
      trustServerCertificate: String(process.env.DB_TRUST_CERT || 'true') === 'true'
    },
    pool: {
      max: 10,
      min: 0,
      idleTimeoutMillis: 30000
    }
  }
};
