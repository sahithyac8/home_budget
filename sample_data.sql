-- Optional demo data. Run after schema.sql (python init_db.py --demo, or the mysql command line).
-- It creates ONE demo account:  demo@example.com  /  Demo@1234  (a public demo login, not a real one).
-- Running it a second time stops with a "duplicate email" error, so the numbers never double.
USE home_budget;

INSERT INTO users (full_name, email, password_hash)
VALUES ('Demo User', 'demo@example.com', 'pbkdf2:sha256:600000$E45ghbHIgC1TDDxQ$999e7bcd86ce96bc6aad02d9361f6b85b5390531183a6ca847e94bc7a6e60e23');
SET @uid = LAST_INSERT_ID();

INSERT INTO categories (user_id, category_name, category_type) VALUES
 (@uid,'Salary','income'), (@uid,'Business','income'), (@uid,'Interest','income'), (@uid,'Other Income','income'),
 (@uid,'Groceries','expense'), (@uid,'Rent','expense'), (@uid,'Transportation','expense'),
 (@uid,'Healthcare','expense'), (@uid,'Education','expense'), (@uid,'Entertainment','expense'),
 (@uid,'Utilities','expense'), (@uid,'Other Expense','expense');

INSERT INTO transactions (user_id, transaction_date, transaction_type, category_id, amount, description)
SELECT @uid, d, t, (SELECT category_id FROM categories WHERE user_id = @uid AND category_name = n AND category_type = t), a, ds FROM (
  SELECT '2026-09-01' d,'income'  t,'Salary' n,60000.00 a,'September salary' ds UNION ALL
  SELECT '2026-09-03','expense','Rent',15000.00,'September rent' UNION ALL
  SELECT '2026-09-07','expense','Groceries',6200.00,'Monthly groceries' UNION ALL
  SELECT '2026-09-12','expense','Transportation',2100.00,'Fuel and bus pass' UNION ALL
  SELECT '2026-09-18','expense','Entertainment',1800.00,'Movies and dining' UNION ALL
  SELECT '2026-10-01','income','Salary',60000.00,'October salary' UNION ALL
  SELECT '2026-10-02','income','Interest',1500.00,'Savings interest' UNION ALL
  SELECT '2026-10-03','expense','Rent',15000.00,'October rent' UNION ALL
  SELECT '2026-10-06','expense','Groceries',7800.00,'Groceries and festival shopping' UNION ALL
  SELECT '2026-10-10','expense','Healthcare',3200.00,'Doctor visit and medicines' UNION ALL
  SELECT '2026-10-15','expense','Education',4500.00,'Course fees' UNION ALL
  SELECT '2026-10-20','expense','Entertainment',3900.00,'Weekend trip'
) x;

INSERT INTO monthly_budgets (user_id, category_id, budget_month, budget_year, budget_amount)
SELECT @uid, category_id, 10, 2026, b FROM (
  SELECT 'Groceries' n, 7000.00 b UNION ALL SELECT 'Rent',15000.00 UNION ALL
  SELECT 'Healthcare',3000.00 UNION ALL SELECT 'Entertainment',3000.00 UNION ALL
  SELECT 'Education',5000.00
) y JOIN categories c ON c.user_id = @uid AND c.category_name = y.n AND c.category_type = 'expense';

-- ---------------------------------------------------------------------------
-- Edge cases for August 2026 (used by the tests and the demonstration):
--   * a month with NO income  -> negative savings, savings rate shown as 0%
--   * a transaction with NO description (NULL)
--   * Groceries spent exactly 100% of its budget  -> Warning, not Over (boundary)
--   * Utilities spent exactly 80% of its budget   -> Warning (boundary)
--   * Transportation has a budget but no spending -> 0% used, status OK
-- ---------------------------------------------------------------------------
INSERT INTO transactions (user_id, transaction_date, transaction_type, category_id, amount, description)
SELECT @uid, d, t, (SELECT category_id FROM categories WHERE user_id = @uid AND category_name = n AND category_type = t), a, ds FROM (
  SELECT '2026-08-03' d,'expense' t,'Rent' n,15000.00 a,'August rent' ds UNION ALL
  SELECT '2026-08-09','expense','Groceries',5600.00,'Monthly groceries' UNION ALL
  SELECT '2026-08-14','expense','Utilities',2000.00,NULL
) x;

INSERT INTO monthly_budgets (user_id, category_id, budget_month, budget_year, budget_amount)
SELECT @uid, category_id, 8, 2026, b FROM (
  SELECT 'Groceries' n, 5600.00 b UNION ALL SELECT 'Utilities',2500.00 UNION ALL
  SELECT 'Transportation',2000.00 UNION ALL SELECT 'Rent',15000.00
) y JOIN categories c ON c.user_id = @uid AND c.category_name = y.n AND c.category_type = 'expense';
