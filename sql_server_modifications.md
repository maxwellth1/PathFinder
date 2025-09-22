# SQL Server Modifications Guide

## 1. Update System Prompt in `/src/database/agent.py`

Change line 19 from:
```python
You are a specialized SQL query agent for a jewellery company's business intelligence system. Your role is to generate syntactically correct MySQL queries based on business questions and provide clear, actionable answers.
```

To:
```python
You are a specialized SQL query agent for a jewellery company's business intelligence system. Your role is to generate syntactically correct SQL Server queries based on business questions and provide clear, actionable answers.
```

Change line 24 from:
```python
- Generate **READ-ONLY** MySQL queries exclusively
```

To:
```python
- Generate **READ-ONLY** SQL Server queries exclusively
```

## 2. Update Schema Syntax

SQL Server uses different syntax for some features:

### Auto-increment columns
MySQL: `id BIGINT NOT NULL AUTO_INCREMENT`
SQL Server: `id BIGINT IDENTITY(1,1) NOT NULL`

### Boolean fields
MySQL: `TINYINT(1)`
SQL Server: `BIT`

### String length specifications
MySQL: `VARCHAR(30)`
SQL Server: `VARCHAR(30)` or `NVARCHAR(30)` for Unicode

### Date functions
MySQL: `DATE()`, `NOW()`
SQL Server: `CAST(... AS DATE)`, `GETDATE()`

## 3. Example Updated Schema for SQL Server

```sql
CREATE TABLE basic_subscription (
    id BIGINT IDENTITY(1,1) NOT NULL, 
    cost DECIMAL(10, 2) NOT NULL, 
    duration SMALLINT NOT NULL, 
    status NVARCHAR(10) NOT NULL, 
    created_on DATETIME2 NOT NULL, 
    plan_id BIGINT, 
    user_id BIGINT, 
    code NVARCHAR(20), 
    last_paid_on DATE, 
    last_tried_on DATETIME2, 
    closing_date DATETIME2, 
    invoice_no NVARCHAR(500), 
    seen BIT NOT NULL, 
    skip_save BIT NOT NULL, 
    completed_date DATETIME2, 
    pending_installment SMALLINT NOT NULL, 
    note NVARCHAR(500), 
    net_cost DECIMAL(10, 2) NOT NULL, 
    sync_id CHAR(32) NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT FK_basic_subscription_plan 
        FOREIGN KEY(plan_id) REFERENCES basic_savingsplan (id), 
    CONSTRAINT FK_basic_subscription_user 
        FOREIGN KEY(user_id) REFERENCES basic_user (id)
);
```