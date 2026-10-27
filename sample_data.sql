-- Optional demo data. Run after schema.sql:  mysql -u root -p home_budget < sample_data.sql
USE home_budget;

INSERT INTO transactions (transaction_date, transaction_type, category_id, amount, description)
SELECT d, t, (SELECT category_id FROM categories WHERE category_name = n AND category_type = t), a, ds FROM (
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

INSERT INTO monthly_budgets (category_id, budget_month, budget_year, budget_amount)
SELECT category_id, 10, 2026, b FROM (
  SELECT 'Groceries' n, 7000.00 b UNION ALL SELECT 'Rent',15000.00 UNION ALL
  SELECT 'Healthcare',3000.00 UNION ALL SELECT 'Entertainment',3000.00 UNION ALL
  SELECT 'Education',5000.00
) y JOIN categories c ON c.category_name = y.n AND c.category_type = 'expense';

-- ---------------------------------------------------------------------------
-- Edge cases for August 2026 (used by the tests and the demonstration):
--   * a month with NO income  -> negative savings, savings rate shown as 0%
--   * a transaction with NO description (NULL)
--   * Groceries spent exactly 100% of its budget  -> Warning, not Over (boundary)
--   * Utilities spent exactly 80% of its budget   -> Warning (boundary)
--   * Transportation has a budget but no spending -> 0% used, status OK
-- ---------------------------------------------------------------------------
INSERT INTO transactions (transaction_date, transaction_type, category_id, amount, description)
SELECT d, t, (SELECT category_id FROM categories WHERE category_name = n AND category_type = t), a, ds FROM (
  SELECT '2026-08-03' d,'expense' t,'Rent' n,15000.00 a,'August rent' ds UNION ALL
  SELECT '2026-08-09','expense','Groceries',5600.00,'Monthly groceries' UNION ALL
  SELECT '2026-08-14','expense','Utilities',2000.00,NULL
) x;

INSERT INTO monthly_budgets (category_id, budget_month, budget_year, budget_amount)
SELECT category_id, 8, 2026, b FROM (
  SELECT 'Groceries' n, 5600.00 b UNION ALL SELECT 'Utilities',2500.00 UNION ALL
  SELECT 'Transportation',2000.00 UNION ALL SELECT 'Rent',15000.00
) y JOIN categories c ON c.category_name = y.n AND c.category_type = 'expense';
