-- Testing ke liye dummy books
USE library_db;

INSERT INTO books (title, author, isbn, category, total_copies, available_copies) VALUES
('Let Us C', 'Yashavant Kanetkar', '9788183331630', 'Programming', 5, 5),
('Python Crash Course', 'Eric Matthes', '9781593279288', 'Programming', 3, 3),
('Database System Concepts', 'Silberschatz', '9780078022159', 'Database', 2, 2),
('Wings of Fire', 'A. P. J. Abdul Kalam', '9788173711466', 'Biography', 4, 4),
('Discovery of India', 'Jawaharlal Nehru', '9780143031031', 'History', 2, 2);
