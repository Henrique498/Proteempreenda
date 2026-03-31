const { getRequest, sql } = require('../config/db');

async function createPayment({
  subscriptionId,
  userId,
  planId,
  provider,
  providerPaymentId,
  valor,
  currency,
  status,
  metadataJson
}) {
  const request = await getRequest();
  request.input('subscriptionId', sql.BigInt, subscriptionId);
  request.input('userId', sql.Int, userId);
  request.input('planId', sql.Int, planId);
  request.input('provider', sql.NVarChar(40), provider || 'manual');
  request.input('providerPaymentId', sql.NVarChar(100), providerPaymentId || null);
  request.input('valor', sql.Decimal(10, 2), valor);
  request.input('currency', sql.Char(3), currency || 'BRL');
  request.input('status', sql.NVarChar(20), status);
  request.input('metadataJson', sql.NVarChar(sql.MAX), metadataJson || null);

  const result = await request.query(`
    INSERT INTO dbo.Payments
      (SubscriptionId, UserId, PlanId, Provider, ProviderPaymentId, Valor, Currency, Status, PaidAt, MetadataJson)
    OUTPUT
      INSERTED.Id,
      INSERTED.SubscriptionId,
      INSERTED.UserId,
      INSERTED.PlanId,
      INSERTED.Provider,
      INSERTED.ProviderPaymentId,
      INSERTED.Valor,
      INSERTED.Currency,
      INSERTED.Status,
      INSERTED.PaidAt,
      INSERTED.MetadataJson,
      INSERTED.CreatedAt,
      INSERTED.UpdatedAt
    VALUES
      (
        @subscriptionId,
        @userId,
        @planId,
        @provider,
        @providerPaymentId,
        @valor,
        @currency,
        @status,
        CASE WHEN @status = N'paid' THEN SYSUTCDATETIME() ELSE NULL END,
        @metadataJson
      )
  `);

  return result.recordset[0];
}

async function listByUserId(userId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);

  const result = await request.query(`
    SELECT
      Pay.Id,
      Pay.SubscriptionId,
      Pay.UserId,
      Pay.PlanId,
      Pay.Provider,
      Pay.ProviderPaymentId,
      Pay.Valor,
      Pay.Currency,
      Pay.Status,
      Pay.PaidAt,
      Pay.CreatedAt,
      P.Slug AS PlanSlug,
      P.Nome AS PlanNome
    FROM dbo.Payments Pay
    INNER JOIN dbo.Plans P ON P.Id = Pay.PlanId
    WHERE Pay.UserId = @userId
    ORDER BY Pay.CreatedAt DESC, Pay.Id DESC
  `);

  return result.recordset;
}

module.exports = {
  createPayment,
  listByUserId
};
