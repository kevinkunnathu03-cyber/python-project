"""Student Management System - Python + SQLite, command line.

Default logins (first run): admin/admin123, teacher1/teacher123, alice/alice123
"""
import getpass
import hashlib
import os
import sqlite3
from contextlib import closing

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")
current_user = None  

def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=()):
    """Run a SELECT and return all rows."""
    with closing(connect()) as conn:
        return conn.execute(sql, params).fetchall()


def change(sql, params=()):
    """Run INSERT / UPDATE / DELETE and save it."""
    with closing(connect()) as conn:
        with conn:
            return conn.execute(sql, params).lastrowid


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def setup_database():
    with closing(connect()) as conn:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    username  TEXT NOT NULL UNIQUE,
                    password  TEXT NOT NULL,
                    role      TEXT NOT NULL CHECK (role IN ('admin','teacher','student')),
                    full_name TEXT NOT NULL,
                    phone     TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS courses (
                    course_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_name TEXT NOT NULL UNIQUE,
                    credits     INTEGER NOT NULL CHECK (credits > 0)
                );
                CREATE TABLE IF NOT EXISTS grades (
                    grade_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    course_id  INTEGER NOT NULL,
                    marks      REAL NOT NULL CHECK (marks BETWEEN 0 AND 100),
                    UNIQUE (student_id, course_id),
                    FOREIGN KEY (student_id) REFERENCES users (user_id) ON DELETE CASCADE,
                    FOREIGN KEY (course_id) REFERENCES courses (course_id) ON DELETE RESTRICT
                );
            """)
    if not query("SELECT 1 FROM users"):  
        users = [("admin", "admin123", "admin", "School Admin", "9000000001"),
                 ("teacher1", "teacher123", "teacher", "Mr. Brown", "9000000002"),
                 ("alice", "alice123", "student", "Alice Smith", "9876543210"),
                 ("ben", "ben123", "student", "Ben Taylor", "9123456780")]
        for username, pw, role, name, phone in users:
            change("INSERT INTO users (username, password, role, full_name, phone) "
                   "VALUES (?, ?, ?, ?, ?)", (username, hash_pw(pw), role, name, phone))
        for course in [("Mathematics", 4), ("Physics", 3), ("English", 2)]:
            change("INSERT INTO courses (course_name, credits) VALUES (?, ?)", course)
        for grade in [(3, 1, 88), (3, 2, 72.5), (4, 1, 61), (4, 3, 95)]:
            change("INSERT INTO grades (student_id, course_id, marks) VALUES (?, ?, ?)", grade)


def ask(prompt, default=None):
    """Ask until the user types something (Enter keeps the default, if any)."""
    while True:
        text = input(prompt).strip()
        if text:
            return text
        if default is not None:
            return str(default)
        print("Input cannot be empty.")


def ask_number(prompt, kind=int, minimum=0, maximum=None, default=None):
    while True:
        try:
            value = kind(ask(prompt, default))
            if value != value:  
                raise ValueError
            if value < minimum:
                print(f"Enter a value of at least {minimum}.")
            elif maximum is not None and value > maximum:
                print(f"Enter a value of at most {maximum}.")
            else:
                return value
        except ValueError:
            print("Enter a valid number.")


def ask_phone(prompt, default=None):
    while True:
        phone = ask(prompt, default)
        if phone.isascii() and phone.isdigit() and 7 <= len(phone) <= 15:
            return phone
        print("Phone must be 7-15 digits.")


def ask_yes(prompt):
    return input(prompt + " (y/n): ").strip().lower() == "y"


def show(headers, rows):
    if not rows:
        print("No records found.")
        return
    print(" | ".join(headers))
    print("-" * 60)
    for row in rows:
        print(" | ".join(str(item) for item in row))

def register(role="student"):
    username = ask("Username: ").lower()
    if query("SELECT 1 FROM users WHERE username = ?", (username,)):
        print("That username is already taken.")
        return
    while True:
        password = getpass.getpass("Password (min 6 characters): ")
        if len(password) >= 6:
            break
        print("Password is too short.")
    name = ask("Full name: ")
    phone = ask_phone("Phone: ")
    change("INSERT INTO users (username, password, role, full_name, phone) "
           "VALUES (?, ?, ?, ?, ?)", (username, hash_pw(password), role, name, phone))
    print(f"{role.capitalize()} account created.")


def add_student():
    register("student")


def add_teacher():
    register("teacher")


def login():
    global current_user
    for attempt in range(3):
        username = ask("Username: ").lower()
        password = getpass.getpass("Password: ")
        rows = query("SELECT user_id, full_name, role FROM users "
                     "WHERE username = ? AND password = ?", (username, hash_pw(password)))
        if rows:
            current_user = {"id": rows[0][0], "name": rows[0][1], "role": rows[0][2]}
            print(f"Welcome, {current_user['name']}!")
            return True
        print(f"Wrong username or password. Attempts left: {2 - attempt}")
    return False


def logout():
    global current_user
    current_user = None
    print("Logged out.")

def list_users():
    sql = "SELECT user_id, username, role, full_name, phone FROM users"
    if current_user["role"] == "teacher":
        sql += " WHERE role = 'student'" 
    show(["ID", "Username", "Role", "Name", "Phone"], query(sql))


def find_user():
    """Ask for a user ID and return (id, name, phone, role) or None."""
    rows = query("SELECT user_id, full_name, phone, role FROM users WHERE user_id = ?",
                 (ask_number("User ID: ", minimum=1),))
    if not rows or (current_user["role"] == "teacher" and rows[0][3] != "student"):
        print("No such user.")
        return None
    return rows[0]


def update_user():
    user = find_user()
    if user:
        print("Press Enter to keep the current value.")
        name = ask(f"Name [{user[1]}]: ", user[1])
        phone = ask_phone(f"Phone [{user[2]}]: ", user[2])
        change("UPDATE users SET full_name = ?, phone = ? WHERE user_id = ?",
               (name, phone, user[0]))
        print("Updated.")


def delete_user():
    user = find_user()
    if not user:
        return
    if user[0] == current_user["id"]:
        print("You cannot delete your own account.")
    elif ask_yes(f"Delete {user[1]} and all their grades?"):
        change("DELETE FROM users WHERE user_id = ?", (user[0],))
        print("Deleted.")


def my_profile():
    rows = query("SELECT user_id, username, full_name, phone FROM users WHERE user_id = ?",
                 (current_user["id"],))
    show(["ID", "Username", "Name", "Phone"], rows)


def list_courses():
    show(["ID", "Course", "Credits"], query("SELECT * FROM courses"))


def add_course():
    name = ask("Course name: ")
    credits = ask_number("Credits: ", minimum=1, maximum=20)
    change("INSERT INTO courses (course_name, credits) VALUES (?, ?)", (name, credits))
    print("Course added.")


def find_course():
    rows = query("SELECT * FROM courses WHERE course_id = ?",
                 (ask_number("Course ID: ", minimum=1),))
    if not rows:
        print("No such course.")
    return rows[0] if rows else None


def update_course():
    course = find_course()
    if course:
        print("Press Enter to keep the current value.")
        name = ask(f"Name [{course[1]}]: ", course[1])
        credits = ask_number(f"Credits [{course[2]}]: ", minimum=1, maximum=20,
                             default=course[2])
        change("UPDATE courses SET course_name = ?, credits = ? WHERE course_id = ?",
               (name, credits, course[0]))
        print("Course updated.")


def delete_course():
    course = find_course()
    if course and ask_yes(f"Delete course {course[1]}?"):
        change("DELETE FROM courses WHERE course_id = ?", (course[0],)) 
        print("Course deleted.")


def list_grades(only_mine=False):
    sql = ("SELECT g.grade_id, u.full_name, c.course_name, g.marks, "
           "CASE WHEN g.marks >= 90 THEN 'A' WHEN g.marks >= 75 THEN 'B' "
           "WHEN g.marks >= 60 THEN 'C' WHEN g.marks >= 40 THEN 'D' ELSE 'F' END "
           "FROM grades g JOIN users u ON u.user_id = g.student_id "
           "JOIN courses c ON c.course_id = g.course_id")
    params = []
    if only_mine:
        sql += " WHERE g.student_id = ?"
        params.append(current_user["id"])
    show(["ID", "Student", "Course", "Marks", "Grade"], query(sql + " ORDER BY g.grade_id", params))


def my_grades():
    list_grades(only_mine=True)


def add_grade():
    user = find_user()
    if not user:
        return
    if user[3] != "student":
        print("Grades can only be given to students.")
        return
    list_courses()
    course = find_course()
    if not course:
        return
    if query("SELECT 1 FROM grades WHERE student_id = ? AND course_id = ?", (user[0], course[0])):
        print("This student already has marks for that course. Use 'Update marks'.")
        return
    marks = ask_number("Marks (0-100): ", float, 0, 100)
    change("INSERT INTO grades (student_id, course_id, marks) VALUES (?, ?, ?)",
           (user[0], course[0], marks))
    print("Marks saved.")


def find_grade():
    rows = query("SELECT grade_id, marks FROM grades WHERE grade_id = ?",
                 (ask_number("Grade ID: ", minimum=1),))
    if not rows:
        print("No such grade record.")
    return rows[0] if rows else None


def update_grade():
    grade = find_grade()
    if grade:
        marks = ask_number(f"New marks [{grade[1]}]: ", float, 0, 100, grade[1])
        change("UPDATE grades SET marks = ? WHERE grade_id = ?", (marks, grade[0]))
        print("Marks updated.")


def delete_grade():
    grade = find_grade()
    if grade and ask_yes("Delete this grade record?"):
        change("DELETE FROM grades WHERE grade_id = ?", (grade[0],))
        print("Deleted.")

def run_menu(title, options, exit_text="Back"):
    while True:
        print(f"\n=== {title} ===")
        for number, (label, _) in enumerate(options, 1):
            print(f"{number}. {label}")
        print(f"0. {exit_text}")
        try:
            choice = int(input("Choose an option: ").strip())
        except ValueError:
            print("Invalid choice. Type a number from the menu.")
            continue
        if choice == 0:
            return
        if not 1 <= choice <= len(options):
            print("Invalid choice. Pick a number from the menu.")
            continue
        try:
            options[choice - 1][1]()
        except sqlite3.IntegrityError:
            print("Error: duplicate value, or the record is linked to other records.")
        except sqlite3.Error as error:
            print(f"Database error: {error}")
        except KeyboardInterrupt:
            print("\nCancelled.")
        except EOFError:
            raise
        except Exception as error:
            print(f"Unexpected error: {error}")


def role_menu():
    role = current_user["role"]
    if role == "admin":
        options = [("Add teacher account", add_teacher), ("Add student", add_student),
                   ("View users", list_users), ("Update user", update_user),
                   ("Delete user", delete_user), ("View courses", list_courses),
                   ("Add course", add_course), ("Update course", update_course),
                   ("Delete course", delete_course), ("Add marks", add_grade),
                   ("View grades", list_grades), ("Update marks", update_grade),
                   ("Delete grade record", delete_grade)]
    elif role == "teacher":
        options = [("Add student", add_student), ("View students", list_users),
                   ("Update student", update_user), ("View courses", list_courses),
                   ("Add marks", add_grade), ("View grades", list_grades),
                   ("Update marks", update_grade)]
    else:
        options = [("My profile", my_profile), ("View courses", list_courses),
                   ("My grades", my_grades)]
    run_menu(f"{role.upper()} MENU", options, "Logout")
    logout()


def main():
    try:
        setup_database()
    except (sqlite3.Error, OSError) as error:
        print(f"Could not set up the database: {error}")
        return
    try:
        while True:
            print("\n=== STUDENT MANAGEMENT SYSTEM ===\n1. Login\n2. Register as student\n0. Exit")
            choice = input("Choose an option: ").strip()
            if choice == "1":
                if login():
                    role_menu()
            elif choice == "2":
                try:
                    register()
                except sqlite3.Error as error:
                    print(f"Database error: {error}")
            elif choice == "0":
                print("Goodbye!")
                return
            else:
                print("Invalid choice. Type 1, 2 or 0.")
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")


if __name__ == "__main__":
    main()