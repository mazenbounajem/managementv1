-- Fix Auxiliary table to make 'id' column IDENTITY
-- Run this script on your SQL Server database

USE POSDb;  -- Replace with your database name if different

-- Step 1: Check current table structure and data
SELECT TOP 5 * FROM Auxiliary ORDER BY id DESC;

-- Step 2: Find the maximum current id value
DECLARE @max_id INT;
SELECT @max_id = MAX(id) FROM Auxiliary;
PRINT 'Current max id: ' + CAST(@max_id AS VARCHAR(10));

-- Step 3: Create a temporary table to hold existing data
SELECT * INTO Auxiliary_temp FROM Auxiliary;

-- Step 4: Drop the existing table
DROP TABLE Auxiliary;

-- Step 5: Create the table with correct schema (id as IDENTITY)
CREATE TABLE [dbo].[Auxiliary](
    [id] [int] IDENTITY(1,1) NOT NULL,
    [LedgerId] [int] NOT NULL,
    [ParentId] [int] NULL,
    [AccountNumber] [int] NOT NULL,
    [GroupAccountId] [int] NULL,
    [JobAccountId] [int] NULL,
    [ShortCut] [nvarchar](50) NULL,
    [Name] [nvarchar](100) NOT NULL,
    [Status] [int] NOT NULL,
    [UpdateDate] [datetime] NOT NULL,
    [TimeStamp] [timestamp] NOT NULL,
    CONSTRAINT [PK_Auxiliary] PRIMARY KEY CLUSTERED ([id] ASC)
);

-- Step 6: Insert data back from temporary table (without id column)
SET IDENTITY_INSERT Auxiliary ON;

INSERT INTO Auxiliary (id, LedgerId, ParentId, AccountNumber, GroupAccountId, JobAccountId, ShortCut, Name, Status, UpdateDate, TimeStamp)
SELECT id, LedgerId, ParentId, AccountNumber, GroupAccountId, JobAccountId, ShortCut, Name, Status, UpdateDate, TimeStamp
FROM Auxiliary_temp;

SET IDENTITY_INSERT Auxiliary OFF;

-- Step 7: Drop temporary table
DROP TABLE Auxiliary_temp;

-- Step 8: Reseed the IDENTITY to continue from the correct value
DECLARE @max_id_final INT;
SELECT @max_id_final = MAX(id) FROM Auxiliary;
DBCC CHECKIDENT ('Auxiliary', RESEED, @max_id_final);

-- Step 9: Verify the fix
SELECT TOP 5 * FROM Auxiliary ORDER BY id DESC;
PRINT 'Auxiliary table fixed successfully! The id column is now IDENTITY.';
