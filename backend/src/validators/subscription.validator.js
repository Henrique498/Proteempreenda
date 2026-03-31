const { z } = require('zod');

const checkoutSchema = z.object({
  planSlug: z.string().min(2).max(60),
  billingCycle: z.enum(['mensal', 'anual']).default('mensal'),
  paymentMethod: z.enum(['cartao', 'pix', 'boleto', 'manual']).default('manual'),
  cardLast4: z.string().regex(/^\d{4}$/).optional()
});

const cancelSubscriptionParamsSchema = z.object({
  id: z.coerce.number().int().positive()
});

module.exports = {
  checkoutSchema,
  cancelSubscriptionParamsSchema
};
