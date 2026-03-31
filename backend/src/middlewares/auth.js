const { verifyToken } = require('../utils/jwt');

function requireAuth(req, res, next) {
  const authHeader = req.headers.authorization || '';
  const [, token] = authHeader.split(' ');

  if (!token) {
    return res.status(401).json({ error: true, message: 'Token ausente' });
  }

  try {
    req.user = verifyToken(token);
    return next();
  } catch (e) {
    return res.status(401).json({ error: true, message: 'Token inválido' });
  }
}

module.exports = { requireAuth };
