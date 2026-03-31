const userRepository = require('../repositories/user.repository');

async function getMe(userId) {
  const user = await userRepository.findById(userId);
  if (!user) {
    const err = new Error('Usuário não encontrado');
    err.status = 404;
    throw err;
  }

  return {
    Id: user.Id,
    Nome: user.Nome,
    Email: user.Email,
    Tipo: user.Tipo,
    Ativo: user.Ativo,
    UltimoLoginEm: user.UltimoLoginEm || null,
    CreatedAt: user.CreatedAt || null
  };
}

module.exports = {
  getMe
};
