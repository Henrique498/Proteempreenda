function errorHandler(err, req, res, next) {
  const status = err.status || 500;
  const message = err.message || 'Erro interno do servidor';

  if (status >= 500) {
    console.error('[ERROR]', err);
  }

  res.status(status).json({
    error: true,
    message
  });
}

module.exports = errorHandler;
