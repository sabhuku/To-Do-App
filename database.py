import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional
import hashlib
import os

class Database:
    def __init__(self, db_path: str = "todo_app.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create tasks table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            due_date DATE,
            priority TEXT NOT NULL,
            recurrence TEXT NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Create tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')

        # Create task_tags table for many-to-many relationship
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_tags (
            task_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id),
            PRIMARY KEY (task_id, tag_id)
        )
        ''')

        conn.commit()
        conn.close()

    def create_user(self, username: str, password: str) -> bool:
        """Create a new user. Returns True if successful, False if username exists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def verify_user(self, username: str, password: str) -> Optional[int]:
        """Verify user credentials. Returns user_id if valid, None if invalid."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None

    def add_task(self, user_id: int, task_data: Dict) -> int:
        """Add a new task and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert task
            cursor.execute('''
            INSERT INTO tasks (user_id, title, description, category, due_date, 
                             priority, recurrence, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                task_data['title'],
                task_data.get('description', ''),
                task_data.get('category', 'Other'),
                task_data.get('due_date'),
                task_data.get('priority', 'Medium'),
                task_data.get('recurrence', 'None'),
                False
            ))
            task_id = cursor.lastrowid

            # Handle tags
            for tag_name in task_data.get('tags', []):
                # Insert or get tag
                cursor.execute(
                    "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                    (tag_name,)
                )
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                tag_id = cursor.fetchone()[0]

                # Link tag to task
                cursor.execute(
                    "INSERT INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                    (task_id, tag_id)
                )

            conn.commit()
            return task_id
        finally:
            conn.close()

    def get_tasks(self, user_id: int) -> List[Dict]:
        """Get all tasks for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
        SELECT t.*, GROUP_CONCAT(tg.name) as tags
        FROM tasks t
        LEFT JOIN task_tags tt ON t.id = tt.task_id
        LEFT JOIN tags tg ON tt.tag_id = tg.id
        WHERE t.user_id = ?
        GROUP BY t.id
        ''', (user_id,))

        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            task['tags'] = task['tags'].split(',') if task['tags'] else []
            task['due_date'] = datetime.strptime(task['due_date'], '%Y-%m-%d').date() if task['due_date'] else None
            task['created_at'] = datetime.strptime(task['created_at'], '%Y-%m-%d %H:%M:%S')
            tasks.append(task)

        conn.close()
        return tasks

    def update_task(self, task_id: int, user_id: int, task_data: Dict) -> bool:
        """Update a task. Returns True if successful."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Update task
            cursor.execute('''
            UPDATE tasks 
            SET title = ?, description = ?, category = ?, due_date = ?,
                priority = ?, recurrence = ?, completed = ?
            WHERE id = ? AND user_id = ?
            ''', (
                task_data['title'],
                task_data.get('description', ''),
                task_data.get('category', 'Other'),
                task_data.get('due_date'),
                task_data.get('priority', 'Medium'),
                task_data.get('recurrence', 'None'),
                task_data.get('completed', False),
                task_id,
                user_id
            ))

            # Update tags
            cursor.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
            for tag_name in task_data.get('tags', []):
                cursor.execute(
                    "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                    (tag_name,)
                )
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                tag_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                    (task_id, tag_id)
                )

            conn.commit()
            return True
        finally:
            conn.close()

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a task. Returns True if successful."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
            cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_all_tags(self, user_id: int) -> List[str]:
        """Get all unique tags used by a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT DISTINCT tg.name
        FROM tags tg
        JOIN task_tags tt ON tg.id = tt.tag_id
        JOIN tasks t ON tt.task_id = t.id
        WHERE t.user_id = ?
        ''', (user_id,))

        tags = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tags 