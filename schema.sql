-- Home Budget (Expense Tracker) schema for MySQL 8.0.16+
-- Every table that holds money data has a user_id, so each person only ever sees their own records.
CREATE DATABASE IF NOT EXISTS home_budget CHARACTER SET utf8mb4;
USE home_budget;

CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    full_name     VARCHAR(60)  NOT NULL,
    email         VARCHAR(120) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,          -- a salted hash, never the password itself
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_email (email)
) ENGINE=InnoDB;

-- Each user gets their own copy of the 12 default categories when they register (see auth.py).
CREATE TABLE IF NOT EXISTS categories (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    category_name VARCHAR(50) NOT NULL,
    category_type ENUM('income','expense') NOT NULL,
    CONSTRAINT fk_category_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uq_category (user_id, category_name, category_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id          INT NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_type ENUM('income','expense') NOT NULL,
    category_id      INT NOT NULL,
    amount           DECIMAL(12,2) NOT NULL,
    description      VARCHAR(255) NULL,
    CONSTRAINT chk_amount_positive CHECK (amount > 0),
    CONSTRAINT fk_txn_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_txn_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id) ON DELETE RESTRICT,
    INDEX idx_txn_user_date (user_id, transaction_date),
    INDEX idx_txn_category (category_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS monthly_budgets (
    budget_id     INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    category_id   INT NOT NULL,
    budget_month  TINYINT NOT NULL,
    budget_year   SMALLINT NOT NULL,
    budget_amount DECIMAL(12,2) NOT NULL,
    CONSTRAINT chk_budget_month CHECK (budget_month BETWEEN 1 AND 12),
    CONSTRAINT chk_budget_amount CHECK (budget_amount > 0),
    CONSTRAINT fk_budget_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_budget_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id) ON DELETE CASCADE,
    UNIQUE KEY uq_budget (user_id, category_id, budget_month, budget_year)
) ENGINE=InnoDB;

-- Month-wise categories: which expense categories a user keeps for a given month.
-- Suggestions are calculated from earlier months (see month_categories.py); a row here records the
-- user's own choice: 'added' (pinned to the month) or 'dismissed' (a suggestion the user deleted).
CREATE TABLE IF NOT EXISTS month_categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    category_id INT NOT NULL,
    cat_year    SMALLINT NOT NULL,
    cat_month   TINYINT NOT NULL,
    status      ENUM('added','dismissed') NOT NULL,
    CONSTRAINT fk_mc_user FOREIGN KEY (user_id)
        REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_mc_category FOREIGN KEY (category_id)
        REFERENCES categories(category_id) ON DELETE CASCADE,
    UNIQUE KEY uq_month_category (user_id, category_id, cat_year, cat_month)
) ENGINE=InnoDB;
