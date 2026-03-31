const bcrypt = require('bcryptjs');
const userRepository = require('../repositories/user.repository');
const { signToken } = require('../utils/jwt');

async function register(input) {
  const existing = await userRepository.findByEmail(input.email);
  if (existing) {
    const err = new Error('E-mail já cadastrado');
    err.status = 409;
    throw err;
  }

  const senhaHash = await bcrypt.hash(input.senha, 10);
  const user = await userRepository.createUser({
    nome: input.nome,
    email: input.email,
    senhaHash,
    tipo: input.tipo || 'responsavel'
  });

  const token = signToken({ sub: user.Id, tipo: user.Tipo, email: user.Email });
  return {
    user: {
      Id: user.Id,
      Nome: user.Nome,
      Email: user.Email,
      Tipo: user.Tipo
    },
    token
  };
}

async function login({ email, senha }) {
  const user = await userRepository.findByEmail(email);
  if (!user || !user.Ativo) {
    const err = new Error('Credenciais inválidas');
    err.status = 401;
    throw err;
  }

  const ok = await bcrypt.compare(senha, user.SenhaHash);
  if (!ok) {
    const err = new Error('Credenciais inválidas');
    err.status = 401;
    throw err;
  }

  await userRepository.touchLastLogin(user.Id);

  const token = signToken({ sub: user.Id, tipo: user.Tipo, email: user.Email });
  return {
    user: {
      Id: user.Id,
      Nome: user.Nome,
      Email: user.Email,
      Tipo: user.Tipo
    },
    token
  };
}

module.exports = {
  register,
  login
};
