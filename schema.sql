-- Library Management System: MySQL schema
-- You can also import this file in phpMyAdmin or MySQL Workbench.

CREATE DATABASE IF NOT EXISTS library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library_db;

DROP TABLE IF EXISTS issues;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;

-- 1. Users: the librarian (admin) and the members (students)
CREATE TABLE users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          ENUM('admin', 'member') NOT NULL DEFAULT 'member',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_role_name (role, name)
) ENGINE=InnoDB;

-- 2. Books
CREATE TABLE books (
    book_id          INT AUTO_INCREMENT PRIMARY KEY,
    title            VARCHAR(200) NOT NULL,
    author           VARCHAR(120) NOT NULL,
    isbn             VARCHAR(20) UNIQUE,
    category         VARCHAR(60),
    total_copies     INT NOT NULL DEFAULT 1,
    available_copies INT NOT NULL DEFAULT 1,
    INDEX idx_books_title (title),
    INDEX idx_books_available (available_copies)
) ENGINE=InnoDB;

-- 3. Issues (the library version of the 'Records' table from Milestone 2):
--    which member took which book, and when it was issued and returned
CREATE TABLE issues (
    issue_id    INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    book_id     INT NOT NULL,
    issue_date  DATE NOT NULL,
    due_date    DATE NOT NULL,
    return_date DATE NULL,
    fine        INT NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id),
    INDEX idx_issues_open (return_date, due_date),
    INDEX idx_issues_user_open (user_id, return_date)
) ENGINE=InnoDB;
