import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import hashlib
import os
import secrets
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "todo.db"):
        self.db_path = db_path
        logger.debug(f"Initializing database at {db_path}")
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        try:
            if not os.path.exists(self.db_path):
                logger.error(f"Database file {self.db_path} does not exist!")
            else:
                logger.debug(f"Database file {self.db_path} exists.")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                logger.debug("Creating database tables...")
                
                # Create users table with email
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create password_reset_tokens table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        token TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        used BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # Create tasks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        category TEXT,
                        due_date DATE,
                        priority TEXT,
                        completed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # Create tags table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tags (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, name)
                    )
                """)
                
                # Create task_tags table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS task_tags (
                        task_id INTEGER NOT NULL,
                        tag_id INTEGER NOT NULL,
                        PRIMARY KEY (task_id, tag_id),
                        FOREIGN KEY (task_id) REFERENCES tasks (id),
                        FOREIGN KEY (tag_id) REFERENCES tags (id)
                    )
                """)
                
                conn.commit()
                logger.debug("Database tables created successfully")
                logger.debug(f"Database path: {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def create_user(self, username: str, email: str, password: str) -> bool:
        """Create a new user with email."""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                logger.debug(f"Creating new user: {username} with email: {email}")
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                conn.commit()
                logger.debug("User created successfully")
                return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Error creating user: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating user: {str(e)}")
            raise

    def verify_user(self, identifier: str, password: str) -> Optional[int]:
        """Verify user credentials using either username or email."""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                logger.debug(f"Verifying user: {identifier}")
                cursor.execute(
                    "SELECT id FROM users WHERE (username = ? OR email = ?) AND password_hash = ?",
                    (identifier, identifier, password_hash)
                )
                result = cursor.fetchone()
                if result:
                    logger.debug(f"User verified successfully. ID: {result[0]}")
                    return result[0]
                logger.debug("Invalid credentials")
                return None
        except Exception as e:
            logger.error(f"Error verifying user: {str(e)}")
            raise

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user details by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                logger.debug(f"Getting user by ID: {user_id}")
                cursor.execute(
                    "SELECT id, username, email, created_at FROM users WHERE id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    user_dict = {
                        "id": result[0],
                        "username": result[1],
                        "email": result[2],
                        "created_at": result[3]
                    }
                    logger.debug(f"Found user: {user_dict}")
                    return user_dict
                logger.debug(f"No user found with ID: {user_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            raise

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user details by email."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, created_at FROM users WHERE email = ?",
                (email,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "username": result[1],
                    "email": result[2],
                    "created_at": result[3]
                }
            return None

    def get_all_tags(self, user_id: int) -> List[str]:
        """Get all tags for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM tags WHERE user_id = ?",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def add_task(self, user_id: int, task_data: Dict) -> Optional[int]:
        """Add a new task."""
        
        # Format due_date if it's a date object
        due_date_value = task_data.get("due_date")
        if isinstance(due_date_value, date):
            due_date_str = due_date_value.strftime("%Y-%m-%d")
        else:
            # Assume it's either None or already a string (or handle other types if needed)
            due_date_str = due_date_value 
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tasks (user_id, title, description, category, due_date, priority)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    task_data["title"],
                    task_data.get("description"),
                    task_data.get("category"),
                    due_date_str,  # Use the formatted string or original value
                    task_data.get("priority")
                )
            )
            task_id = cursor.lastrowid
            
            # Handle tags
            for tag_name in task_data.get("tags", []):
                # Get or create tag
                cursor.execute(
                    "INSERT OR IGNORE INTO tags (user_id, name) VALUES (?, ?)",
                    (user_id, tag_name)
                )
                cursor.execute(
                    "SELECT id FROM tags WHERE user_id = ? AND name = ?",
                    (user_id, tag_name)
                )
                tag_id = cursor.fetchone()[0]
                
                # Link tag to task
                cursor.execute(
                    "INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                    (task_id, tag_id)
                )
            
            conn.commit()
            return task_id

    def get_tasks(self, user_id: int) -> List[Dict]:
        """Get all tasks for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.id, t.title, t.description, t.category, t.due_date, t.priority, t.completed,
                       GROUP_CONCAT(tg.name) as tags
                FROM tasks t
                LEFT JOIN task_tags tt ON t.id = tt.task_id
                LEFT JOIN tags tg ON tt.tag_id = tg.id
                WHERE t.user_id = ?
                GROUP BY t.id
                """,
                (user_id,)
            )
            tasks = []
            for row in cursor.fetchall():
                due_date_obj = None
                if row[4]: # Check if due_date string is not None or empty
                    try:
                        due_date_obj = datetime.strptime(row[4], '%Y-%m-%d').date()
                    except ValueError:
                        logger.error(f"Invalid date format for task {row[0]}: {row[4]}")
                        # Keep due_date_obj as None if parsing fails

                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "category": row[3],
                    "due_date": due_date_obj, # Use the converted date object or None
                    "priority": row[5],
                    "completed": row[6] == 1, # Ensure completed is boolean
                    "tags": row[7].split(",") if row[7] else []
                })
            logger.debug(f"Retrieved tasks for user {user_id}: {tasks}")
            return tasks

    def update_task(self, task_id: int, user_id: int, task_data: Dict) -> bool:
        """Update an existing task for a specific user."""
        if not task_data: # No data provided to update
            return False

        # Dynamically build the SET part of the SQL query
        set_parts = []
        values = []
        for key, value in task_data.items():
            # Basic validation/mapping if needed (e.g., boolean to int for SQLite)
            if isinstance(value, bool):
                value = 1 if value else 0
            elif isinstance(value, date):
                value = value.strftime("%Y-%m-%d")
                
            # Ensure the key is a valid column name (add more columns as needed)
            if key in ["title", "description", "category", "due_date", "priority", "completed"]:
                 set_parts.append(f"{key} = ?")
                 values.append(value)

        if not set_parts: # No valid fields to update
            logger.warning("No valid fields provided for task update.")
            return False

        sql = f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = ? AND user_id = ?"
        values.extend([task_id, user_id])

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, tuple(values))
                conn.commit()
                logger.info(f"Task {task_id} for user {user_id} updated successfully with data: {task_data}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating task {task_id} for user {user_id}: {e}")
            return False

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def create_password_reset_token(self, email: str) -> Optional[str]:
        """Create a password reset token for a user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get user by email
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            result = cursor.fetchone()
            if not result:
                return None
            
            user_id = result[0]
            
            # Generate token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # Token valid for 24 hours
            
            # Store token
            cursor.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (?, ?, ?)
                """,
                (user_id, token, expires_at)
            )
            
            conn.commit()
            return token

    def verify_reset_token(self, token: str) -> Optional[int]:
        """Verify a password reset token and return user_id if valid."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT user_id FROM password_reset_tokens
                WHERE token = ? AND expires_at > ? AND used = FALSE
                """,
                (token, datetime.now())
            )
            
            result = cursor.fetchone()
            return result[0] if result else None

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a user's password using a valid token."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get user_id from token
            user_id = self.verify_reset_token(token)
            if not user_id:
                return False
            
            # Update password
            password_hash = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id)
            )
            
            # Mark token as used
            cursor.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE token = ?",
                (token,)
            )
            
            conn.commit()
            return True 