function errorHandler(err, req, res, next) {
  const status = err.status || 500;
  const message = err.message || 'Erro interno do servidor';

  if (status >= 500) {
    console.error('[ERROR]', err);
  }

  const payload = {
    error: true,
    message
  };

  if (err.code) payload.code = err.code;
  if (err.details) payload.details = err.details;
  if (err.paidPlans) payload.paidPlans = err.paidPlans;

  res.status(status).json(payload);
}

module.exports = errorHandler;
