const { getRequest, sql } = require('../config/db');

async function getCurrentByUserId(userId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);
  const result = await request.query(`
    SELECT TOP 1
      S.Id,
      S.UserId,
      S.PlanId,
      S.Status,
      S.BillingCycle,
      S.StartAt,
      S.EndAt,
      S.NextBillingAt,
      S.CancelAtPeriodEnd,
      S.UpdatedAt,
      P.Slug AS PlanSlug,
      P.Nome AS PlanNome,
      P.PrecoMensal,
      P.PrecoAnualTotal
    FROM dbo.UserSubscriptions S
    INNER JOIN dbo.Plans P ON P.Id = S.PlanId
    WHERE S.UserId = @userId
      AND S.Status IN (N'trial', N'active', N'past_due')
    ORDER BY S.UpdatedAt DESC, S.Id DESC
  `);

  return result.recordset[0] || null;
}

async function listByUserId(userId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);

  const result = await request.query(`
    SELECT
      S.Id,
      S.UserId,
      S.PlanId,
      S.Status,
      S.BillingCycle,
      S.StartAt,
      S.EndAt,
      S.NextBillingAt,
      S.CancelAtPeriodEnd,
      S.CreatedAt,
      S.UpdatedAt,
      P.Slug AS PlanSlug,
      P.Nome AS PlanNome,
      P.PrecoMensal,
      P.PrecoAnualTotal
    FROM dbo.UserSubscriptions S
    INNER JOIN dbo.Plans P ON P.Id = S.PlanId
    WHERE S.UserId = @userId
    ORDER BY S.CreatedAt DESC, S.Id DESC
  `);

  return result.recordset;
}

async function cancelActiveByUserId(userId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);

  await request.query(`
    UPDATE dbo.UserSubscriptions
    SET
      Status = N'canceled',
      EndAt = COALESCE(EndAt, SYSUTCDATETIME()),
      CancelAtPeriodEnd = 0,
      UpdatedAt = SYSUTCDATETIME()
    WHERE UserId = @userId
      AND Status IN (N'trial', N'active', N'past_due')
  `);
}

async function createSubscription({ userId, planId, billingCycle, status }) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);
  request.input('planId', sql.Int, planId);
  request.input('billingCycle', sql.NVarChar(10), billingCycle);
  request.input('status', sql.NVarChar(20), status);

  const result = await request.query(`
    DECLARE @now DATETIME2(0) = SYSUTCDATETIME();
    DECLARE @endAt DATETIME2(0) = CASE
      WHEN @billingCycle = N'anual' THEN DATEADD(YEAR, 1, @now)
      ELSE DATEADD(MONTH, 1, @now)
    END;

    INSERT INTO dbo.UserSubscriptions
      (UserId, PlanId, Status, BillingCycle, StartAt, EndAt, NextBillingAt, CancelAtPeriodEnd)
    OUTPUT
      INSERTED.Id,
      INSERTED.UserId,
      INSERTED.PlanId,
      INSERTED.Status,
      INSERTED.BillingCycle,
      INSERTED.StartAt,
      INSERTED.EndAt,
      INSERTED.NextBillingAt,
      INSERTED.CancelAtPeriodEnd,
      INSERTED.CreatedAt,
      INSERTED.UpdatedAt
    VALUES
      (@userId, @planId, @status, @billingCycle, @now, @endAt, @endAt, 0)
  `);

  return result.recordset[0];
}

async function cancelByIdForUser(subscriptionId, userId) {
  const request = await getRequest();
  request.input('subscriptionId', sql.BigInt, subscriptionId);
  request.input('userId', sql.Int, userId);

  const result = await request.query(`
    UPDATE dbo.UserSubscriptions
    SET
      Status = N'canceled',
      EndAt = COALESCE(EndAt, SYSUTCDATETIME()),
      CancelAtPeriodEnd = 0,
      UpdatedAt = SYSUTCDATETIME()
    OUTPUT
      INSERTED.Id,
      INSERTED.UserId,
      INSERTED.PlanId,
      INSERTED.Status,
      INSERTED.BillingCycle,
      INSERTED.StartAt,
      INSERTED.EndAt,
      INSERTED.NextBillingAt,
      INSERTED.CancelAtPeriodEnd,
      INSERTED.CreatedAt,
      INSERTED.UpdatedAt
    WHERE Id = @subscriptionId
      AND UserId = @userId
  `);

  return result.recordset[0] || null;
}

module.exports = {
  getCurrentByUserId,
  listByUserId,
  cancelActiveByUserId,
  createSubscription,
  cancelByIdForUser
};
