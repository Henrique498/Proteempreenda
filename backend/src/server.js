const app = require('./app');
const env = require('./config/env');
const { connectDb } = require('./config/db');

async function bootstrap() {
  await connectDb();
  app.listen(env.port, () => {
    console.log(`API rodando em http://localhost:${env.port}`);
  });
}

bootstrap().catch((err) => {
  console.error('Falha ao iniciar API:', err.message);
  process.exit(1);
});
