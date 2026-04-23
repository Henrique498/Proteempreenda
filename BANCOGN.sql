USE master;
EXEC xp_instance_regwrite
    N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'LoginMode', REG_DWORD, 2;   -- 1 = só Windows | 2 = misto
GO

SELECT @@SERVERNAME;
SELECT name FROM sys.databases;
SELECT SERVERPROPERTY('IsIntegratedSecurityOnly') AS SomenteWindows;
GO


-- LOGIN E USUÁRIO SQL SERVER (autenticação SQL)

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'guardiannet_userr')
BEGIN
    CREATE LOGIN guardiannet_userr
    WITH PASSWORD    = 'GuardianNet@2026',
         CHECK_POLICY      = OFF,
         CHECK_EXPIRATION  = OFF;
END
GO

USE EMPREENDA;
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'guardiannet_userr')
BEGIN
    CREATE USER guardiannet_userr FOR LOGIN guardiannet_userr;
    ALTER ROLE db_owner ADD MEMBER guardiannet_userr;
END
GO

USE master;
GO

IF DB_ID(N'EMPREENDA') IS NOT NULL
BEGIN
    ALTER DATABASE EMPREENDA SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE EMPREENDA;
END
GO

CREATE DATABASE EMPREENDA COLLATE Latin1_General_CI_AS;
GO

USE EMPREENDA;
GO


-- Planos
CREATE TABLE dbo.Planos (
    Id          INT           IDENTITY(1,1) NOT NULL,
    Nome        NVARCHAR(50)  NOT NULL,
    Descricao   NVARCHAR(255) NULL,
    ValorMensal DECIMAL(10,2) NOT NULL CONSTRAINT DF_Planos_ValorMensal DEFAULT 0,
    ValorAnual  DECIMAL(10,2) NOT NULL CONSTRAINT DF_Planos_ValorAnual  DEFAULT 0,
    Ativo       BIT           NOT NULL CONSTRAINT DF_Planos_Ativo       DEFAULT 1,
    CriadoEm   DATETIME2(0)  NOT NULL CONSTRAINT DF_Planos_CriadoEm    DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_Planos PRIMARY KEY (Id)
);
GO

--Usuários 
-- SenhaHash nunca é retornada pela API. Soft delete via Ativo = 0.
CREATE TABLE dbo.Usuarios (
    Id           INT           IDENTITY(1,1) NOT NULL,
    Nome         NVARCHAR(150) NOT NULL,
    Email        NVARCHAR(200) NOT NULL,
    SenhaHash    NVARCHAR(256) NULL,
    Telefone     NVARCHAR(20)  NULL,
    Tipo         NVARCHAR(20)  NOT NULL CONSTRAINT DF_Usuarios_Tipo     DEFAULT 'usuario',
    Ativo        BIT           NOT NULL CONSTRAINT DF_Usuarios_Ativo    DEFAULT 1,
    CriadoEm    DATETIME2(0)  NOT NULL CONSTRAINT DF_Usuarios_CriadoEm DEFAULT SYSUTCDATETIME(),
    AtualizadoEm DATETIME2(0) NULL,

    CONSTRAINT PK_Usuarios       PRIMARY KEY (Id),
    CONSTRAINT UQ_Usuarios_Email UNIQUE      (Email),
    CONSTRAINT CK_Usuarios_Tipo  CHECK       (Tipo IN ('usuario', 'admin'))
);

CREATE INDEX IX_Usuarios_Email ON dbo.Usuarios (Email);
GO

-- Hash SHA-256 do token (nunca texto claro). Soft delete via Revogado = 1.
CREATE TABLE dbo.AuthTokens (
    Id         INT           IDENTITY(1,1) NOT NULL,
    UserId     INT           NOT NULL,
    TokenHash  NVARCHAR(64)  NOT NULL,
    ExpiraEm   DATETIME2(0)  NOT NULL,
    Revogado   BIT           NOT NULL CONSTRAINT DF_AuthTokens_Revogado DEFAULT 0,
    CriadoEm  DATETIME2(0)  NOT NULL CONSTRAINT DF_AuthTokens_CriadoEm DEFAULT SYSUTCDATETIME(),
    RevogadoEm DATETIME2(0) NULL,

    CONSTRAINT PK_AuthTokens PRIMARY KEY (Id),
    CONSTRAINT FK_AuthTokens_Usuarios
        FOREIGN KEY (UserId) REFERENCES dbo.Usuarios (Id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IX_AuthTokens_TokenHash ON dbo.AuthTokens (TokenHash);
CREATE        INDEX IX_AuthTokens_UserId    ON dbo.AuthTokens (UserId);
CREATE        INDEX IX_AuthTokens_ExpiraEm  ON dbo.AuthTokens (ExpiraEm);
GO

-- Assinaturas 
-- Soft delete via Status = 'cancelada'.
CREATE TABLE dbo.Assinaturas (
    Id         INT           IDENTITY(1,1) NOT NULL,
    UsuarioId  INT           NOT NULL,
    PlanoId    INT           NOT NULL,
    Periodo    NVARCHAR(20)  NOT NULL,
    DataInicio DATETIME2(0)  NOT NULL CONSTRAINT DF_Assinaturas_DataInicio DEFAULT SYSUTCDATETIME(),
    DataFim    DATETIME2(0)  NULL,
    Status     NVARCHAR(20)  NOT NULL CONSTRAINT DF_Assinaturas_Status     DEFAULT 'ativa',
    CriadoEm  DATETIME2(0)  NOT NULL CONSTRAINT DF_Assinaturas_CriadoEm   DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_Assinaturas        PRIMARY KEY (Id),
    CONSTRAINT CK_Assinaturas_Periodo CHECK (Periodo IN ('mensal', 'anual')),
    CONSTRAINT CK_Assinaturas_Status  CHECK (Status  IN ('ativa', 'cancelada', 'expirada', 'pendente')),
    CONSTRAINT FK_Assinaturas_Usuarios
        FOREIGN KEY (UsuarioId) REFERENCES dbo.Usuarios (Id) ON DELETE CASCADE,
    CONSTRAINT FK_Assinaturas_Planos
        FOREIGN KEY (PlanoId)   REFERENCES dbo.Planos   (Id) ON DELETE CASCADE
);

CREATE INDEX IX_Assinaturas_UsuarioId ON dbo.Assinaturas (UsuarioId);
CREATE INDEX IX_Assinaturas_Status    ON dbo.Assinaturas (Status);
GO

-- 3.5 Pagamentos
-- Delete físico nunca ocorre (auditoria financeira). Soft delete via Status = 'estornado'.
CREATE TABLE dbo.Pagamentos (
    Id            INT           IDENTITY(1,1) NOT NULL,
    AssinaturaId  INT           NOT NULL,
    Valor         DECIMAL(10,2) NOT NULL,
    Metodo        NVARCHAR(20)  NOT NULL,
    Status        NVARCHAR(20)  NOT NULL CONSTRAINT DF_Pagamentos_Status  DEFAULT 'pendente',
    DataPagamento DATETIME2(0)  NULL,
    CriadoEm     DATETIME2(0)  NOT NULL CONSTRAINT DF_Pagamentos_CriadoEm DEFAULT SYSUTCDATETIME(),

    CONSTRAINT PK_Pagamentos        PRIMARY KEY (Id),
    CONSTRAINT CK_Pagamentos_Metodo CHECK (Metodo IN ('pix', 'cartao', 'boleto')),
    CONSTRAINT CK_Pagamentos_Status CHECK (Status  IN ('pendente', 'aprovado', 'recusado', 'estornado')),
    CONSTRAINT FK_Pagamentos_Assinaturas
        FOREIGN KEY (AssinaturaId) REFERENCES dbo.Assinaturas (Id) ON DELETE CASCADE
);

CREATE INDEX IX_Pagamentos_AssinaturaId ON dbo.Pagamentos (AssinaturaId);
CREATE INDEX IX_Pagamentos_Status       ON dbo.Pagamentos (Status);
GO

-- ContatosConfiaveis 
CREATE TABLE dbo.ContatosConfiaveis (
    Id              INT           IDENTITY(1,1) NOT NULL,
    UsuarioId       INT           NOT NULL,
    Nome            NVARCHAR(150) NOT NULL,
    Relacao         NVARCHAR(40)  NOT NULL,
    PaisCodigo      CHAR(2)       NULL,
    DDI             NVARCHAR(6)   NULL,
    Numero          NVARCHAR(30)  NOT NULL,
    NumeroFormatado NVARCHAR(50)  NULL,
    Ativo           BIT           NOT NULL CONSTRAINT DF_ContatosConfiaveis_Ativo    DEFAULT 1,
    CriadoEm        DATETIME2(0)  NOT NULL CONSTRAINT DF_ContatosConfiaveis_CriadoEm DEFAULT SYSUTCDATETIME(),
    AtualizadoEm    DATETIME2(0)  NULL,

    CONSTRAINT PK_ContatosConfiaveis PRIMARY KEY (Id),
    CONSTRAINT FK_ContatosConfiaveis_Usuarios
        FOREIGN KEY (UsuarioId) REFERENCES dbo.Usuarios (Id) ON DELETE CASCADE
);

CREATE INDEX IX_ContatosConfiaveis_UsuarioId_Ativo
    ON dbo.ContatosConfiaveis (UsuarioId, Ativo, CriadoEm DESC);
GO

-- Visão consolidada para o dashboard do usuário

CREATE VIEW dbo.vw_Dashboard AS
SELECT
    u.Id        AS UsuarioId,
    u.Nome,
    u.Email,
    u.Telefone,
    p.Nome      AS Plano,
    a.Id        AS AssinaturaId,
    a.Periodo,
    a.Status    AS StatusAssinatura,
    a.DataInicio,
    a.DataFim,
    pg.Id       AS PagamentoId,
    pg.Valor,
    pg.Metodo,
    pg.Status   AS StatusPagamento,
    pg.DataPagamento
FROM       dbo.Usuarios    u
INNER JOIN dbo.Assinaturas a  ON a.UsuarioId     = u.Id
INNER JOIN dbo.Planos      p  ON p.Id            = a.PlanoId
LEFT  JOIN dbo.Pagamentos  pg ON pg.AssinaturaId = a.Id
WHERE u.Ativo = 1;
GO

-- Resumo financeiro para o painel admin (apenas pagamentos aprovados)
CREATE VIEW dbo.vw_ResumoFinanceiro AS
SELECT
    p.Nome          AS Plano,
    a.Periodo,
    COUNT(pg.Id)    AS TotalPagamentos,
    SUM(pg.Valor)   AS ReceitaTotal,
    AVG(pg.Valor)   AS TicketMedio
FROM       dbo.Planos      p
INNER JOIN dbo.Assinaturas a  ON a.PlanoId       = p.Id
INNER JOIN dbo.Pagamentos  pg ON pg.AssinaturaId = a.Id
WHERE pg.Status = 'aprovado'
GROUP BY p.Nome, a.Periodo;
GO




-- Planos 

CREATE OR ALTER PROCEDURE dbo.sp_Planos_Listar
    @ApenasAtivos BIT = 1
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, Nome, Descricao, ValorMensal, ValorAnual, Ativo, CriadoEm
    FROM dbo.Planos
    WHERE (@ApenasAtivos = 0 OR Ativo = 1)
    ORDER BY Id;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Planos_BuscarPorId
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, Nome, Descricao, ValorMensal, ValorAnual, Ativo, CriadoEm
    FROM dbo.Planos WHERE Id = @Id;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Planos_Criar
    @Nome        NVARCHAR(50),
    @Descricao   NVARCHAR(255) = NULL,
    @ValorMensal DECIMAL(10,2) = 0,
    @ValorAnual  DECIMAL(10,2) = 0
AS BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.Planos (Nome, Descricao, ValorMensal, ValorAnual)
    VALUES (@Nome, @Descricao, @ValorMensal, @ValorAnual);
    SELECT SCOPE_IDENTITY() AS NovoId;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Planos_Atualizar
    @Id          INT,
    @Nome        NVARCHAR(50)  = NULL,
    @Descricao   NVARCHAR(255) = NULL,
    @ValorMensal DECIMAL(10,2) = NULL,
    @ValorAnual  DECIMAL(10,2) = NULL,
    @Ativo       BIT           = NULL
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Planos
    SET Nome        = COALESCE(@Nome,        Nome),
        Descricao   = COALESCE(@Descricao,   Descricao),
        ValorMensal = COALESCE(@ValorMensal, ValorMensal),
        ValorAnual  = COALESCE(@ValorAnual,  ValorAnual),
        Ativo       = COALESCE(@Ativo,       Ativo)
    WHERE Id = @Id;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Planos_Desativar
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Planos SET Ativo = 0 WHERE Id = @Id;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

-- Usuários

-- SenhaHash excluída do SELECT (princípio de menor privilégio)
CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_Listar
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, Nome, Email, Telefone, Tipo, Ativo, CriadoEm, AtualizadoEm
    FROM dbo.Usuarios
    ORDER BY CriadoEm DESC;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_BuscarPorId
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, Nome, Email, Telefone, Tipo, Ativo, CriadoEm, AtualizadoEm
    FROM dbo.Usuarios WHERE Id = @Id;
END
GO

-- SenhaHash inclusa: usada somente no serviço de autenticação
CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_BuscarPorEmail
    @Email NVARCHAR(200)
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, Nome, Email, SenhaHash, Telefone, Tipo, Ativo
    FROM dbo.Usuarios WHERE Email = @Email;
END
GO

-- Retorna NovoId = -1 se e-mail já existir (mapeia para HTTP 409 no backend)
CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_Criar
    @Nome      NVARCHAR(150),
    @Email     NVARCHAR(200),
    @SenhaHash NVARCHAR(256),
    @Telefone  NVARCHAR(20) = NULL,
    @Tipo      NVARCHAR(20) = 'usuario'
AS BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM dbo.Usuarios WHERE Email = @Email)
    BEGIN
        SELECT -1 AS NovoId, 'Email já cadastrado.' AS Erro;
        RETURN;
    END
    INSERT INTO dbo.Usuarios (Nome, Email, SenhaHash, Telefone, Tipo)
    VALUES (@Nome, @Email, @SenhaHash, @Telefone, @Tipo);
    SELECT SCOPE_IDENTITY() AS NovoId, NULL AS Erro;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_Atualizar
    @Id       INT,
    @Nome     NVARCHAR(150) = NULL,
    @Telefone NVARCHAR(20)  = NULL,
    @Tipo     NVARCHAR(20)  = NULL,
    @Ativo    BIT           = NULL
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Usuarios
    SET Nome         = COALESCE(@Nome,     Nome),
        Telefone     = COALESCE(@Telefone, Telefone),
        Tipo         = COALESCE(@Tipo,     Tipo),
        Ativo        = COALESCE(@Ativo,    Ativo),
        AtualizadoEm = SYSUTCDATETIME()
    WHERE Id = @Id;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_AlterarSenha
    @Id            INT,
    @NovaSenhaHash NVARCHAR(256)
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Usuarios
    SET SenhaHash    = @NovaSenhaHash,
        AtualizadoEm = SYSUTCDATETIME()
    WHERE Id = @Id AND Ativo = 1;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

-- Soft delete: triggers revogam tokens automaticamente ao desativar
CREATE OR ALTER PROCEDURE dbo.sp_Usuarios_Desativar
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Usuarios
    SET Ativo = 0, AtualizadoEm = SYSUTCDATETIME()
    WHERE Id = @Id;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

-- AuthTokens

CREATE OR ALTER PROCEDURE dbo.sp_AuthTokens_Criar
    @UserId    INT,
    @TokenHash NVARCHAR(64),
    @ExpiraEm  DATETIME2(0)
AS BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.AuthTokens (UserId, TokenHash, ExpiraEm)
    VALUES (@UserId, @TokenHash, @ExpiraEm);
    SELECT SCOPE_IDENTITY() AS NovoId;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_AuthTokens_Validar
    @TokenHash NVARCHAR(64)
AS BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1 Id, UserId, ExpiraEm
    FROM dbo.AuthTokens
    WHERE TokenHash = @TokenHash
      AND Revogado  = 0
      AND ExpiraEm  > SYSUTCDATETIME()
    ORDER BY Id DESC;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_AuthTokens_ListarPorUsuario
    @UserId INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, TokenHash, ExpiraEm, CriadoEm
    FROM dbo.AuthTokens
    WHERE UserId   = @UserId
      AND Revogado = 0
      AND ExpiraEm > SYSUTCDATETIME()
    ORDER BY CriadoEm DESC;
END
GO

-- Revoga token individualmente (logout de sessão única)
CREATE OR ALTER PROCEDURE dbo.sp_AuthTokens_Revogar
    @TokenHash NVARCHAR(64)
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.AuthTokens
    SET Revogado = 1, RevogadoEm = SYSUTCDATETIME()
    WHERE TokenHash = @TokenHash AND Revogado = 0;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

-- Revoga todos os tokens do usuário (troca de senha, desativação)
CREATE OR ALTER PROCEDURE dbo.sp_AuthTokens_RevogarTodas
    @UserId INT
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.AuthTokens
    SET Revogado = 1, RevogadoEm = SYSUTCDATETIME()
    WHERE UserId = @UserId AND Revogado = 0;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

-- Executar via job agendado (ex: SQL Server Agent, diário)
CREATE OR ALTER PROCEDURE dbo.sp_AuthTokens_LimparExpirados
AS BEGIN
    SET NOCOUNT ON;
    DELETE FROM dbo.AuthTokens
    WHERE ExpiraEm < SYSUTCDATETIME() OR Revogado = 1;
    SELECT @@ROWCOUNT AS Removidos;
END
GO

-- ── 6.4  Assinaturas ────────────────────────────────────────────────────

CREATE OR ALTER PROCEDURE dbo.sp_Assinaturas_ListarPorUsuario
    @UsuarioId INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT a.Id, a.UsuarioId, a.PlanoId, p.Nome AS NomePlano,
           a.Periodo, a.DataInicio, a.DataFim, a.Status, a.CriadoEm
    FROM dbo.Assinaturas a
    INNER JOIN dbo.Planos p ON p.Id = a.PlanoId
    WHERE a.UsuarioId = @UsuarioId
    ORDER BY a.CriadoEm DESC;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Assinaturas_BuscarAtiva
    @UsuarioId INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT TOP 1
        a.Id, a.UsuarioId, a.PlanoId, p.Nome AS NomePlano,
        a.Periodo, a.DataInicio, a.DataFim, a.Status, a.CriadoEm
    FROM dbo.Assinaturas a
    INNER JOIN dbo.Planos p ON p.Id = a.PlanoId
    WHERE a.UsuarioId = @UsuarioId
      AND a.Status    = 'ativa'
    ORDER BY a.Id DESC;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Assinaturas_Criar
    @UsuarioId INT,
    @PlanoId   INT,
    @Periodo   NVARCHAR(20)
AS BEGIN
    SET NOCOUNT ON;
    DECLARE @DataInicio DATETIME2(0) = SYSUTCDATETIME();
    DECLARE @DataFim    DATETIME2(0) = CASE @Periodo
        WHEN 'mensal' THEN DATEADD(MONTH,  1, @DataInicio)
        WHEN 'anual'  THEN DATEADD(MONTH, 12, @DataInicio)
    END;
    INSERT INTO dbo.Assinaturas (UsuarioId, PlanoId, Periodo, DataInicio, DataFim, Status)
    VALUES (@UsuarioId, @PlanoId, @Periodo, @DataInicio, @DataFim, 'ativa');
    SELECT SCOPE_IDENTITY() AS NovoId;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Assinaturas_Atualizar
    @Id      INT,
    @PlanoId INT          = NULL,
    @Periodo NVARCHAR(20) = NULL
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Assinaturas
    SET PlanoId = COALESCE(@PlanoId, PlanoId),
        Periodo = COALESCE(@Periodo, Periodo)
    WHERE Id = @Id AND Status = 'ativa';
    SELECT @@ROWCOUNT AS Afetados;
END
GO

-- Cancela a assinatura e estorna pagamentos pendentes (transação atômica)
CREATE OR ALTER PROCEDURE dbo.sp_Assinaturas_Cancelar
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;
        UPDATE dbo.Pagamentos SET Status = 'estornado'
        WHERE AssinaturaId = @Id AND Status = 'pendente';

        UPDATE dbo.Assinaturas
        SET Status = 'cancelada', DataFim = SYSUTCDATETIME()
        WHERE Id = @Id AND Status = 'ativa';
    COMMIT TRANSACTION;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

--Pagamentos 

CREATE OR ALTER PROCEDURE dbo.sp_Pagamentos_ListarPorAssinatura
    @AssinaturaId INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, AssinaturaId, Valor, Metodo, Status, DataPagamento, CriadoEm
    FROM dbo.Pagamentos
    WHERE AssinaturaId = @AssinaturaId
    ORDER BY CriadoEm DESC;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Pagamentos_BuscarPorId
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, AssinaturaId, Valor, Metodo, Status, DataPagamento, CriadoEm
    FROM dbo.Pagamentos WHERE Id = @Id;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Pagamentos_Criar
    @AssinaturaId INT,
    @Valor        DECIMAL(10,2),
    @Metodo       NVARCHAR(20)
AS BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.Pagamentos (AssinaturaId, Valor, Metodo)
    VALUES (@AssinaturaId, @Valor, @Metodo);
    SELECT SCOPE_IDENTITY() AS NovoId;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Pagamentos_AtualizarStatus
    @Id     INT,
    @Status NVARCHAR(20)
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Pagamentos
    SET Status        = @Status,
        DataPagamento = CASE WHEN @Status = 'aprovado' THEN SYSUTCDATETIME() ELSE DataPagamento END
    WHERE Id = @Id;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Pagamentos_Estornar
    @Id INT
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Pagamentos
    SET Status = 'estornado'
    WHERE Id = @Id AND Status = 'aprovado';
    SELECT @@ROWCOUNT AS Afetados;
END
GO

--  Contatos Confiáveis

CREATE OR ALTER PROCEDURE dbo.sp_Contatos_Listar
    @UsuarioId INT
AS BEGIN
    SET NOCOUNT ON;
    SELECT Id, UsuarioId, Nome, Relacao, PaisCodigo, DDI, Numero, NumeroFormatado, Ativo, CriadoEm
    FROM dbo.ContatosConfiaveis
    WHERE UsuarioId = @UsuarioId AND Ativo = 1
    ORDER BY CriadoEm DESC;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Contatos_Criar
    @UsuarioId       INT,
    @Nome            NVARCHAR(150),
    @Relacao         NVARCHAR(40),
    @PaisCodigo      CHAR(2)      = NULL,
    @DDI             NVARCHAR(6)  = NULL,
    @Numero          NVARCHAR(30),
    @NumeroFormatado NVARCHAR(50) = NULL
AS BEGIN
    SET NOCOUNT ON;
    INSERT INTO dbo.ContatosConfiaveis (UsuarioId, Nome, Relacao, PaisCodigo, DDI, Numero, NumeroFormatado)
    VALUES (@UsuarioId, @Nome, @Relacao, @PaisCodigo, @DDI, @Numero, @NumeroFormatado);
    SELECT SCOPE_IDENTITY() AS NovoId;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Contatos_Atualizar
    @Id              INT,
    @UsuarioId       INT,
    @Nome            NVARCHAR(150) = NULL,
    @Relacao         NVARCHAR(40)  = NULL,
    @Numero          NVARCHAR(30)  = NULL,
    @NumeroFormatado NVARCHAR(50)  = NULL
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.ContatosConfiaveis
    SET Nome            = COALESCE(@Nome,            Nome),
        Relacao         = COALESCE(@Relacao,         Relacao),
        Numero          = COALESCE(@Numero,          Numero),
        NumeroFormatado = COALESCE(@NumeroFormatado, NumeroFormatado),
        AtualizadoEm    = SYSUTCDATETIME()
    WHERE Id = @Id AND UsuarioId = @UsuarioId AND Ativo = 1;
    SELECT @@ROWCOUNT AS Afetados;
END
GO

CREATE OR ALTER PROCEDURE dbo.sp_Contatos_Desativar
    @Id        INT,
    @UsuarioId INT
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.ContatosConfiaveis
    SET Ativo = 0, AtualizadoEm = SYSUTCDATETIME()
    WHERE Id = @Id AND UsuarioId = @UsuarioId;
    SELECT @@ROWCOUNT AS Afetados;
END
GO


-- AuthTokens: limpa expirados/revogados a cada novo login 
-- Evita acúmulo infinito de tokens antigos na tabela
CREATE OR ALTER TRIGGER dbo.trg_AuthTokens_LimparExpirados
ON dbo.AuthTokens AFTER INSERT
AS BEGIN
    SET NOCOUNT ON;
    DELETE AT
    FROM dbo.AuthTokens AT
    INNER JOIN inserted i ON AT.UserId = i.UserId
    WHERE AT.ExpiraEm < SYSUTCDATETIME() OR AT.Revogado = 1;
END;
GO

-- Usuários: preenche AtualizadoEm mesmo que o backend esqueça
CREATE OR ALTER TRIGGER dbo.trg_Usuarios_PreencherAtualizadoEm
ON dbo.Usuarios AFTER UPDATE
AS BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE dbo.Usuarios
    SET AtualizadoEm = SYSUTCDATETIME()
    WHERE Id IN (SELECT Id FROM inserted);
END;
GO

-- Usuários: revoga todos os tokens ao desativar conta
-- Garante que sessões abertas sejam invalidadas imediatamente
CREATE OR ALTER TRIGGER dbo.trg_Usuarios_RevogarTokensAoDesativar
ON dbo.Usuarios AFTER UPDATE
AS BEGIN
    SET NOCOUNT ON;
    IF UPDATE(Ativo)
    BEGIN
        UPDATE dbo.AuthTokens
        SET Revogado = 1, RevogadoEm = SYSUTCDATETIME()
        WHERE UserId IN (
            SELECT i.Id FROM inserted i
            INNER JOIN deleted d ON d.Id = i.Id
            WHERE d.Ativo = 1 AND i.Ativo = 0
        )
        AND Revogado = 0;
    END
END;
GO

-- Assinaturas: garante apenas uma assinatura ativa por usuário
-- Race condition protection: cancela assinaturas anteriores ao inserir nova.
CREATE OR ALTER TRIGGER dbo.trg_Assinaturas_UmaAtivaPorUsuario
ON dbo.Assinaturas AFTER INSERT
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Assinaturas
    SET Status  = 'cancelada',
        DataFim = SYSUTCDATETIME()
    WHERE UsuarioId IN (SELECT UsuarioId FROM inserted)
      AND Status    = 'ativa'
      AND Id NOT IN (SELECT Id FROM inserted);
END;
GO

-- Assinaturas: expira automaticamente quando DataFim é atingida ──
CREATE OR ALTER TRIGGER dbo.trg_Assinaturas_ExpirarAutomatica
ON dbo.Assinaturas AFTER UPDATE
AS BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE dbo.Assinaturas
    SET Status = 'expirada'
    WHERE Id IN (SELECT Id FROM inserted)
      AND Status  = 'ativa'
      AND DataFim IS NOT NULL
      AND DataFim < SYSUTCDATETIME();
END;
GO

-- Pagamentos: preenche DataPagamento ao aprovar
CREATE OR ALTER TRIGGER dbo.trg_Pagamentos_PreencherDataPagamento
ON dbo.Pagamentos AFTER INSERT, UPDATE
AS BEGIN
    SET NOCOUNT ON;
    UPDATE dbo.Pagamentos
    SET DataPagamento = SYSUTCDATETIME()
    WHERE Id IN (SELECT Id FROM inserted)
      AND Status        = 'aprovado'
      AND DataPagamento IS NULL;
END;
GO

--  Planos 
INSERT INTO dbo.Planos (Nome, Descricao, ValorMensal, ValorAnual, Ativo) VALUES
    ('Gratuito', 'Trial gratuito de 30 dias sem cartão',          0.00,     0.00, 1),
    ('Basico',   'Proteção essencial para famílias',              9.90,    95.04, 1),
    ('Premium',  'Proteção completa com IA e relatórios',        24.90,   239.04, 1),
    ('Escola',   'Plano institucional para escolas e creches',  149.00,  1430.40, 1);
GO

-- Admin padrão

BEGIN TRY
    BEGIN TRAN;

    DECLARE @AdminEmail NVARCHAR(255) = 'admgn@gmail.com';
    DECLARE @AdminNome  NVARCHAR(120) = 'Administrador GuardianNet';
    DECLARE @AdminHash  NVARCHAR(255) =
        'scrypt:32768:8:1$ZWaXReP6PTGip7AO$4ba336cdd7558597998056eea20fa2d66876aab438483641b4674d6c46785314c01cdab9f01a3535d6d587158d62e51cbb653bd6092256f5d779c4f913a1e8a2';

    IF EXISTS (SELECT 1 FROM dbo.Usuarios WHERE LOWER(Email) = LOWER(@AdminEmail))
    BEGIN
        UPDATE dbo.Usuarios
        SET Nome = @AdminNome, SenhaHash = @AdminHash,
            Tipo = 'admin', Ativo = 1, AtualizadoEm = SYSUTCDATETIME()
        WHERE LOWER(Email) = LOWER(@AdminEmail);
    END
    ELSE
    BEGIN
        INSERT INTO dbo.Usuarios (Nome, Email, SenhaHash, Telefone, Tipo, Ativo)
        VALUES (@AdminNome, @AdminEmail, @AdminHash, NULL, 'admin', 1);
    END

    COMMIT TRAN;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRAN;
    THROW;
END CATCH;
GO

SELECT 'Tabelas'    AS Tipo, name AS Nome FROM sys.tables     WHERE type_desc = 'USER_TABLE' ORDER BY name;
SELECT 'Views'      AS Tipo, name AS Nome FROM sys.views                                      ORDER BY name;
SELECT 'Procedures' AS Tipo, name AS Nome FROM sys.procedures                                 ORDER BY name;
SELECT 'Triggers'   AS Tipo, name AS Nome FROM sys.triggers WHERE parent_class = 1            ORDER BY name;

SELECT 'Planos'     AS Info, * FROM dbo.Planos;
SELECT Id, Nome, Email, Tipo, Ativo FROM dbo.Usuarios WHERE Email = 'admgn@gmail.com';
GO

GO
SELECT * FROM dbo.Usuarios
SELECT * FROM dbo.Planos

SELECT
    a.Id                          AS AssinaturaId,
    u.Id                          AS UsuarioId,
    u.Nome                        AS UsuarioNome,
    u.Email                       AS UsuarioEmail,
    u.Telefone                    AS UsuarioTelefone,
    p.Id                          AS PlanoId,
    p.Nome                        AS PlanoNome,
    p.Descricao                   AS PlanoDescricao,
    a.Periodo                     AS Periodo,
    a.Status                      AS StatusAssinatura,
    a.DataInicio                  AS DataInicioAssinatura,
    a.DataFim                     AS DataFimAssinatura,
    pg.Id                         AS PagamentoId,
    pg.Valor                      AS ValorPagamento,
    pg.Metodo                     AS MetodoPagamento,
    pg.Status                     AS StatusPagamento,
    pg.DataPagamento              AS DataAprovacaoPagamento
FROM dbo.Assinaturas a
INNER JOIN dbo.Usuarios u
    ON u.Id = a.UsuarioId
INNER JOIN dbo.Planos p
    ON p.Id = a.PlanoId
LEFT JOIN dbo.Pagamentos pg
    ON pg.AssinaturaId = a.Id
ORDER BY a.Id DESC, pg.DataPagamento DESC;