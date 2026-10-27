-- Home Budget (Expense Tracker) schema for MySQL 8+
CREATE DATABASE IF NOT EXISTS home_budget CHARACTER SET utf8mb4;
USE home_budget;

CREATE TABLE IF NOT EXISTS categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,
    category_type ENUM('income','expense') NOT NULL,
    UNIQUE KEY uq_category (category_name, category_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   INT AUTO_INCREMENT PRIMARY KEY,
    transaction_date DATE NOT NULL,
    transaction_type ENUM('income','expense') NOT NULL,
    category_id      INT NOT NULL,
    amount           DECIMAL(12,2) NOT NULL,
    description      VARCHAR(255) NULL,
    CONSTRAINT chk_amount_positive CHECK (amount > 0),
    CONSTRAINT fk_txn_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id) ON DELETE RESTRICT,
    INDEX idx_txn_date (transaction_date),
    INDEX idx_txn_category (category_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS monthly_budgets (
    budget_id     INT AUTO_INCREMENT PRIMARY KEY,
    category_id   INT NOT NULL,
    budget_month  TINYINT NOT NULL,
    budget_year   SMALLINT NOT NULL,
    budget_amount DECIMAL(12,2) NOT NULL,
    CONSTRAINT chk_budget_month CHECK (budget_month BETWEEN 1 AND 12),
    CONSTRAINT chk_budget_amount CHECK (budget_amount > 0),
    CONSTRAINT fk_budget_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id) ON DELETE CASCADE,
    UNIQUE KEY uq_budget (category_id, budget_month, budget_year)
) ENGINE=InnoDB;

-- Default categories
INSERT IGNORE INTO categories (category_name, category_type) VALUES
 ('Salary','income'), ('Business','income'), ('Interest','income'), ('Other Income','income'),
 ('Groceries','expense'), ('Rent','expense'), ('Transportation','expense'),
 ('Healthcare','expense'), ('Education','expense'), ('Entertainment','expense'),
 ('Utilities','expense'), ('Other Expense','expense');
