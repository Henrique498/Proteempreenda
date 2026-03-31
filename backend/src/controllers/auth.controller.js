const { registerSchema, loginSchema } = require('../validators/auth.validator');
const authService = require('../services/auth.service');

async function register(req, res, next) {
  try {
    const data = registerSchema.parse(req.body);
    const result = await authService.register(data);
    res.status(201).json(result);
  } catch (e) {
    if (e.name === 'ZodError') {
      return res.status(400).json({ error: true, message: 'Dados inválidos', details: e.issues });
    }
    return next(e);
  }
}

async function login(req, res, next) {
  try {
    const data = loginSchema.parse(req.body);
    const result = await authService.login(data);
    res.json(result);
  } catch (e) {
    if (e.name === 'ZodError') {
      return res.status(400).json({ error: true, message: 'Dados inválidos', details: e.issues });
    }
    return next(e);
  }
}

module.exports = {
  register,
  login
};
