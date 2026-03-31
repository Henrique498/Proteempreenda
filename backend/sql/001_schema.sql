/* =========================================================
   GuardianNet - SQL Server Schema (MVP)
   Execute este script primeiro.
   ========================================================= */

IF DB_ID('GuardianNetDB') IS NULL
BEGIN
  CREATE DATABASE GuardianNetDB;
END
GO

USE GuardianNetDB;
GO

/* USERS */
IF OBJECT_ID('dbo.Users', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Users (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      Nome            NVARCHAR(150) NOT NULL,
      Email           NVARCHAR(200) NOT NULL,
      SenhaHash       NVARCHAR(255) NOT NULL,
      Tipo            NVARCHAR(20)  NOT NULL, -- responsavel|escola|admin
      Ativo           BIT NOT NULL DEFAULT 1,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      UpdatedAt       DATETIME2(0) NULL,
      CONSTRAINT UQ_Users_Email UNIQUE (Email),
      CONSTRAINT CK_Users_Tipo CHECK (Tipo IN ('responsavel','escola','admin'))
  );
END
GO

/* PLANS */
IF OBJECT_ID('dbo.Plans', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Plans (
      Id                  INT IDENTITY(1,1) PRIMARY KEY,
      Slug                NVARCHAR(30) NOT NULL,
      Nome                NVARCHAR(60) NOT NULL,
      PrecoMensal         DECIMAL(10,2) NOT NULL,
      PrecoAnualTotal     DECIMAL(10,2) NOT NULL,
      Ativo               BIT NOT NULL DEFAULT 1,
      CONSTRAINT UQ_Plans_Slug UNIQUE (Slug)
  );
END
GO

/* SUBSCRIPTIONS */
IF OBJECT_ID('dbo.Subscriptions', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Subscriptions (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      UserId          UNIQUEIDENTIFIER NOT NULL,
      PlanId          INT NOT NULL,
      Periodo         NVARCHAR(10) NOT NULL, -- mensal|anual
      Status          NVARCHAR(20) NOT NULL, -- ativa|cancelada|expirada
      InicioEm        DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      FimEm           DATETIME2(0) NULL,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_Subscriptions_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id),
      CONSTRAINT FK_Subscriptions_Plans FOREIGN KEY (PlanId) REFERENCES dbo.Plans(Id),
      CONSTRAINT CK_Subscriptions_Periodo CHECK (Periodo IN ('mensal','anual')),
      CONSTRAINT CK_Subscriptions_Status CHECK (Status IN ('ativa','cancelada','expirada'))
  );
END
GO

/* CHILDREN */
IF OBJECT_ID('dbo.Children', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Children (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      UserId          UNIQUEIDENTIFIER NOT NULL,
      Nome            NVARCHAR(120) NOT NULL,
      DataNascimento  DATE NULL,
      Status          NVARCHAR(20) NOT NULL DEFAULT 'ativo',
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_Children_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id),
      CONSTRAINT CK_Children_Status CHECK (Status IN ('ativo','inativo'))
  );
END
GO

/* TRUSTED CONTACTS */
IF OBJECT_ID('dbo.TrustedContacts', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.TrustedContacts (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      UserId          UNIQUEIDENTIFIER NOT NULL,
      Nome            NVARCHAR(120) NOT NULL,
      Telefone        NVARCHAR(30) NULL,
      Relacao         NVARCHAR(40) NULL,
      IsTrusted       BIT NOT NULL DEFAULT 1,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_TrustedContacts_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id)
  );
END
GO

/* MESSAGES */
IF OBJECT_ID('dbo.Messages', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Messages (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      ChildId         UNIQUEIDENTIFIER NOT NULL,
      OrigemApp       NVARCHAR(50) NULL,
      Conteudo        NVARCHAR(MAX) NULL,
      Tipo            NVARCHAR(20) NOT NULL, -- texto|audio_transcrito
      SenderHash      NVARCHAR(128) NULL,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_Messages_Children FOREIGN KEY (ChildId) REFERENCES dbo.Children(Id),
      CONSTRAINT CK_Messages_Tipo CHECK (Tipo IN ('texto','audio_transcrito'))
  );
END
GO

/* ANALYSIS RESULTS */
IF OBJECT_ID('dbo.AnalysisResults', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.AnalysisResults (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      MessageId       UNIQUEIDENTIFIER NOT NULL,
      RiskLevel       NVARCHAR(20) NOT NULL, -- seguro|atencao|perigo
      Score           DECIMAL(5,4) NULL,
      Categoria       NVARCHAR(80) NULL,
      ModeloVersao    NVARCHAR(40) NULL,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_AnalysisResults_Messages FOREIGN KEY (MessageId) REFERENCES dbo.Messages(Id),
      CONSTRAINT CK_AnalysisResults_Risk CHECK (RiskLevel IN ('seguro','atencao','perigo'))
  );
END
GO

/* ALERTS */
IF OBJECT_ID('dbo.Alerts', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Alerts (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      UserId          UNIQUEIDENTIFIER NOT NULL,
      ChildId         UNIQUEIDENTIFIER NOT NULL,
      AnalysisId      UNIQUEIDENTIFIER NOT NULL,
      Nivel           NVARCHAR(20) NOT NULL, -- seguro|atencao|perigo
      Titulo          NVARCHAR(180) NOT NULL,
      Descricao       NVARCHAR(MAX) NULL,
      Status          NVARCHAR(20) NOT NULL DEFAULT 'pendente', -- pendente|revisado
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      RevisadoEm      DATETIME2(0) NULL,
      CONSTRAINT FK_Alerts_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id),
      CONSTRAINT FK_Alerts_Children FOREIGN KEY (ChildId) REFERENCES dbo.Children(Id),
      CONSTRAINT FK_Alerts_Analysis FOREIGN KEY (AnalysisId) REFERENCES dbo.AnalysisResults(Id),
      CONSTRAINT CK_Alerts_Nivel CHECK (Nivel IN ('seguro','atencao','perigo')),
      CONSTRAINT CK_Alerts_Status CHECK (Status IN ('pendente','revisado'))
  );
END
GO

/* PAYMENTS */
IF OBJECT_ID('dbo.Payments', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.Payments (
      Id              UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID() PRIMARY KEY,
      SubscriptionId  UNIQUEIDENTIFIER NOT NULL,
      Gateway         NVARCHAR(40) NULL,
      Valor           DECIMAL(10,2) NOT NULL,
      Moeda           CHAR(3) NOT NULL DEFAULT 'BRL',
      Status          NVARCHAR(20) NOT NULL, -- aprovado|pendente|recusado|estornado
      TransactionRef  NVARCHAR(120) NULL,
      PaidAt          DATETIME2(0) NULL,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_Payments_Subscriptions FOREIGN KEY (SubscriptionId) REFERENCES dbo.Subscriptions(Id),
      CONSTRAINT CK_Payments_Status CHECK (Status IN ('aprovado','pendente','recusado','estornado'))
  );
END
GO

/* AUDIT LOGS */
IF OBJECT_ID('dbo.AuditLogs', 'U') IS NULL
BEGIN
  CREATE TABLE dbo.AuditLogs (
      Id              BIGINT IDENTITY(1,1) PRIMARY KEY,
      UserId          UNIQUEIDENTIFIER NULL,
      Acao            NVARCHAR(100) NOT NULL,
      Entidade        NVARCHAR(80) NOT NULL,
      EntidadeId      NVARCHAR(64) NULL,
      IpHash          NVARCHAR(128) NULL,
      CreatedAt       DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
      CONSTRAINT FK_AuditLogs_Users FOREIGN KEY (UserId) REFERENCES dbo.Users(Id)
  );
END
GO

/* Índices */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Children_UserId' AND object_id = OBJECT_ID('dbo.Children'))
  CREATE INDEX IX_Children_UserId ON dbo.Children(UserId);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_TrustedContacts_UserId' AND object_id = OBJECT_ID('dbo.TrustedContacts'))
  CREATE INDEX IX_TrustedContacts_UserId ON dbo.TrustedContacts(UserId);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Messages_ChildId_CreatedAt' AND object_id = OBJECT_ID('dbo.Messages'))
  CREATE INDEX IX_Messages_ChildId_CreatedAt ON dbo.Messages(ChildId, CreatedAt DESC);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_AnalysisResults_Risk_CreatedAt' AND object_id = OBJECT_ID('dbo.AnalysisResults'))
  CREATE INDEX IX_AnalysisResults_Risk_CreatedAt ON dbo.AnalysisResults(RiskLevel, CreatedAt DESC);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Alerts_User_Status_CreatedAt' AND object_id = OBJECT_ID('dbo.Alerts'))
  CREATE INDEX IX_Alerts_User_Status_CreatedAt ON dbo.Alerts(UserId, Status, CreatedAt DESC);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Subscriptions_User_Status' AND object_id = OBJECT_ID('dbo.Subscriptions'))
  CREATE INDEX IX_Subscriptions_User_Status ON dbo.Subscriptions(UserId, Status);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_Payments_Subscription_CreatedAt' AND object_id = OBJECT_ID('dbo.Payments'))
  CREATE INDEX IX_Payments_Subscription_CreatedAt ON dbo.Payments(SubscriptionId, CreatedAt DESC);
GO
