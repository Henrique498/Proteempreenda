const userService = require('../services/user.service');

async function me(req, res, next) {
  try {
    const user = await userService.getMe(Number(req.user.sub));
    res.json(user);
  } catch (e) {
    next(e);
  }
}

module.exports = {
  me
};
