const { z } = require('zod');

const registerSchema = z.object({
  nome: z.string().min(2).max(150),
  email: z.string().email().max(200),
  senha: z.string().min(8).max(100),
  tipo: z.enum(['responsavel', 'escola']).optional()
});

const loginSchema = z.object({
  email: z.string().email().max(200),
  senha: z.string().min(8).max(100)
});

module.exports = {
  registerSchema,
  loginSchema
};
