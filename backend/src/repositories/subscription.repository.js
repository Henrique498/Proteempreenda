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
      AND (S.EndAt IS NULL OR S.EndAt > SYSUTCDATETIME())
    ORDER BY S.UpdatedAt DESC, S.Id DESC
  `);

  return result.recordset[0] || null;
}

async function markEndedAsExpiredByUserId(userId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);

  await request.query(`
    UPDATE dbo.UserSubscriptions
    SET
      Status = N'expired',
      UpdatedAt = SYSUTCDATETIME()
    WHERE UserId = @userId
      AND Status IN (N'trial', N'active', N'past_due')
      AND EndAt IS NOT NULL
      AND EndAt <= SYSUTCDATETIME()
  `);
}

async function hasSubscriptionHistoryByUserAndPlan(userId, planId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);
  request.input('planId', sql.Int, planId);

  const result = await request.query(`
    SELECT TOP 1 1 AS HasHistory
    FROM dbo.UserSubscriptions
    WHERE UserId = @userId
      AND PlanId = @planId
  `);

  return Boolean(result.recordset[0]);
}

async function hasUsedAnyFreeTrialByUserId(userId) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);

  const result = await request.query(`
    SELECT TOP 1 1 AS HasUsed
    FROM dbo.UserSubscriptions S
    INNER JOIN dbo.Plans P ON P.Id = S.PlanId
    WHERE S.UserId = @userId
      AND (
        (ISNULL(P.PrecoMensal, 0) <= 0 AND ISNULL(P.PrecoAnualTotal, 0) <= 0)
        OR LOWER(P.Slug) IN (N'gratuito', N'free')
      )
  `);

  return Boolean(result.recordset[0]);
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

async function createTrialSubscription({ userId, planId, trialDays = 30 }) {
  const request = await getRequest();
  request.input('userId', sql.Int, userId);
  request.input('planId', sql.Int, planId);
  request.input('trialDays', sql.Int, trialDays);

  const result = await request.query(`
    DECLARE @now DATETIME2(0) = SYSUTCDATETIME();
    DECLARE @endAt DATETIME2(0) = DATEADD(DAY, @trialDays, @now);

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
      (@userId, @planId, N'trial', N'mensal', @now, @endAt, @endAt, 0)
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
  markEndedAsExpiredByUserId,
  hasSubscriptionHistoryByUserAndPlan,
  hasUsedAnyFreeTrialByUserId,
  listByUserId,
  cancelActiveByUserId,
  createSubscription,
  createTrialSubscription,
  cancelByIdForUser
};
