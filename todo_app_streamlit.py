import streamlit as st
from typing import List, Dict, Set
from datetime import datetime, date, timedelta
import json
from database import Database

class TodoList:
    PRIORITY_LEVELS = ["High", "Medium", "Low"]
    RECURRENCE_OPTIONS = ["None", "Daily", "Weekly", "Monthly"]

    def __init__(self, db: Database, user_id: int):
        self.db = db
        self.user_id = user_id
        if 'categories' not in st.session_state:
            st.session_state.categories = ["Work", "Personal", "Shopping", "Other"]
        if 'tags' not in st.session_state:
            st.session_state.tags = set(self.db.get_all_tags(self.user_id))

    def add_task(self, title: str, description: str = "", category: str = "Other", 
                 due_date: date = None, priority: str = "Medium", tags: List[str] = None,
                 recurrence: str = "None") -> None:
        """Add a new task to the todo list."""
        task_data = {
            "title": title,
            "description": description,
            "category": category,
            "due_date": due_date,
            "priority": priority,
            "tags": tags or [],
            "recurrence": recurrence,
            "completed": False,
        }
        task_id = self.db.add_task(self.user_id, task_data)
        if task_id:
            st.success(f"Task added successfully! ID: {task_id}")
            # Update tags in session state
            st.session_state.tags.update(tags or [])

    def edit_task(self, task_id: int, title: str, description: str, category: str, 
                  due_date: date, priority: str, tags: List[str], recurrence: str) -> None:
        """Edit an existing task."""
        task_data = {
            "title": title,
            "description": description,
            "category": category,
            "due_date": due_date,
            "priority": priority,
            "tags": tags,
            "recurrence": recurrence
        }
        if self.db.update_task(task_id, self.user_id, task_data):
            st.success(f"Task {task_id} updated successfully!")
            # Update tags in session state
            st.session_state.tags.update(tags)
        else:
            st.error(f"Failed to update task {task_id}")

    def mark_completed(self, task_id: int) -> None:
        """Mark a task as completed."""
        task_data = {"completed": True}
        if self.db.update_task(task_id, self.user_id, task_data):
            return
        st.error(f"Task with ID {task_id} not found.")

    def delete_task(self, task_id: int) -> None:
        """Delete a task from the todo list."""
        if self.db.delete_task(task_id, self.user_id):
            st.success(f"Task {task_id} deleted successfully!")
        else:
            st.error(f"Task with ID {task_id} not found.")

    def view_tasks(self) -> None:
        """Display all tasks in the todo list."""
        tasks = self.db.get_tasks(self.user_id)
        if not tasks:
            st.warning("No tasks found in the todo list.")
            return

        # Add custom CSS for colored checkmarks, tooltips, and due date styling
        st.markdown("""
            <style>
            .task-complete {
                color: #00ff00;
                font-size: 1.2rem;
                margin-bottom: 0.5rem;
            }
            .task-incomplete {
                color: #808080;
                font-size: 1.2rem;
                margin-bottom: 0.5rem;
                cursor: pointer;
            }
            .task-incomplete:hover {
                color: #00ff00;
            }
            .overdue {
                color: #ff0000;
                font-weight: bold;
            }
            .due-today {
                color: #ffa500;
                font-weight: bold;
            }
            .due-soon {
                color: #ffd700;
            }
            </style>
        """, unsafe_allow_html=True)

        # Add view options
        view_option = st.radio("View Tasks By:", ["List", "Calendar"])
        
        if view_option == "Calendar":
            self.show_calendar_view(tasks)
        else:
            self.show_list_view(tasks)

    def show_calendar_view(self, tasks: List[Dict]) -> None:
        """Display tasks in a calendar view."""
        from datetime import datetime, timedelta
        import calendar
        
        # Get current month and year
        today = datetime.now().date()
        current_month = today.month
        current_year = today.year
        
        # Create month navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("Previous Month"):
                if current_month == 1:
                    current_month = 12
                    current_year -= 1
                else:
                    current_month -= 1
        with col2:
            st.subheader(f"{calendar.month_name[current_month]} {current_year}")
        with col3:
            if st.button("Next Month"):
                if current_month == 12:
                    current_month = 1
                    current_year += 1
                else:
                    current_month += 1
        
        # Get the calendar for the current month
        cal = calendar.monthcalendar(current_year, current_month)
        
        # Create a grid for the calendar
        st.write("")
        cols = st.columns(7)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            cols[i].write(f"**{day}**")
        
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].write("")
                    continue
                
                current_date = datetime(current_year, current_month, day).date()
                day_tasks = [task for task in tasks if task["due_date"] == current_date]
                
                if day_tasks:
                    with cols[i].expander(f"{day} ({len(day_tasks)})"):
                        for task in day_tasks:
                            self.display_task(task)
                else:
                    cols[i].write(day)

    def show_list_view(self, tasks: List[Dict]) -> None:
        """Display tasks in a list view with filtering and sorting."""
        # Add filtering and sorting options
        st.subheader("Filter and Sort Tasks")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_category = st.selectbox("Filter by Category", ["All"] + list(st.session_state.categories))
            search_query = st.text_input("Search Tasks", "")
        
        with col2:
            selected_priority = st.selectbox("Filter by Priority", ["All"] + self.PRIORITY_LEVELS)
            selected_tags = st.multiselect("Filter by Tags", list(st.session_state.tags))
        
        with col3:
            show_completed = st.checkbox("Show Completed Tasks", value=True)
            sort_by = st.selectbox("Sort By", ["Due Date", "Priority", "Created Date"])

        # Filter tasks
        filtered_tasks = tasks

        if selected_category != "All":
            filtered_tasks = [task for task in filtered_tasks if task["category"] == selected_category]
        if selected_priority != "All":
            filtered_tasks = [task for task in filtered_tasks if task["priority"] == selected_priority]
        if selected_tags:
            filtered_tasks = [task for task in filtered_tasks if any(tag in task["tags"] for tag in selected_tags)]
        if not show_completed:
            filtered_tasks = [task for task in filtered_tasks if not task["completed"]]
        if search_query:
            search_lower = search_query.lower()
            filtered_tasks = [
                task for task in filtered_tasks 
                if search_lower in task["title"].lower() 
                or search_lower in task["description"].lower()
                or search_lower in task["category"].lower()
            ]

        # Sort tasks
        if sort_by == "Due Date":
            filtered_tasks.sort(key=lambda x: (x["due_date"] is None, x["due_date"]))
        elif sort_by == "Priority":
            priority_order = {"High": 0, "Medium": 1, "Low": 2}
            filtered_tasks.sort(key=lambda x: priority_order[x["priority"]])
        else:  # Created Date
            filtered_tasks.sort(key=lambda x: x["created_at"])

        st.subheader("=== Todo List ===")
        for task in filtered_tasks:
            self.display_task(task)

    def display_task(self, task: Dict) -> None:
        """Display a single task with due date styling."""
        from datetime import datetime, timedelta
        
        col1, col2, col3 = st.columns([1, 10, 1])
        
        with col1:
            check_class = "task-complete" if task["completed"] else "task-incomplete"
            if task["completed"]:
                st.markdown(f'<div class="{check_class}">✓</div>', unsafe_allow_html=True)
            else:
                if st.button("✓", key=f"complete_{task['id']}", help="Click to mark as completed"):
                    self.mark_completed(task['id'])
                    st.experimental_rerun()
            if st.button("🗑️", key=f"delete_{task['id']}", help="Delete task"):
                self.delete_task(task['id'])
        
        with col2:
            priority_color = {
                "High": "🔴",
                "Medium": "🟡",
                "Low": "🟢"
            }
            
            # Add due date styling
            due_date_style = ""
            if not task["completed"] and task["due_date"]:
                today = datetime.now().date()
                due_date = task["due_date"]
                if due_date < today:
                    due_date_style = "overdue"
                elif due_date == today:
                    due_date_style = "due-today"
                elif (due_date - today).days <= 3:
                    due_date_style = "due-soon"
            
            title_style = "text-decoration: line-through; color: #808080;" if task["completed"] else ""
            st.markdown(
                f"{priority_color[task['priority']]} <span style='{title_style}'>**{task['id']}. {task['title']}**</span>",
                unsafe_allow_html=True
            )
            st.markdown(f"**Category:** {task['category']} | **Priority:** {task['priority']}")
            if task["description"]:
                description_style = "color: #808080;" if task["completed"] else ""
                st.markdown(f"<span style='{description_style}'>Description: {task['description']}</span>", unsafe_allow_html=True)
            if task["due_date"]:
                st.markdown(f"<span class='{due_date_style}'>Due: {task['due_date'].strftime('%Y-%m-%d')}</span>", unsafe_allow_html=True)
            if task["recurrence"] != "None":
                recurrence_style = "color: #808080;" if task["completed"] else ""
                st.markdown(f"<span style='{recurrence_style}'>Recurrence: {task['recurrence']}</span>", unsafe_allow_html=True)
            if task["tags"]:
                tags_style = "color: #808080;" if task["completed"] else ""
                st.markdown(f"<span style='{tags_style}'>Tags: " + ", ".join([f"`{tag}`" for tag in task["tags"]]) + "</span>", unsafe_allow_html=True)
            created_style = "color: #808080;" if task["completed"] else ""
            st.markdown(f"<span style='{created_style}'>Created: {task['created_at'].strftime('%Y-%m-%d %H:%M:%S')}</span>", unsafe_allow_html=True)
        
        with col3:
            if not task["completed"] and st.button("✏️", key=f"edit_{task['id']}", help="Edit task"):
                self.show_edit_form(task)
        st.divider()

    def show_edit_form(self, task: Dict) -> None:
        """Show form to edit a task."""
        with st.form(f"edit_form_{task['id']}"):
            st.subheader(f"Edit Task {task['id']}")
            new_title = st.text_input("Title", value=task["title"])
            new_description = st.text_area("Description", value=task["description"])
            new_category = st.selectbox("Category", st.session_state.categories, 
                                      index=st.session_state.categories.index(task["category"]))
            new_priority = st.selectbox("Priority", self.PRIORITY_LEVELS,
                                      index=self.PRIORITY_LEVELS.index(task["priority"]))
            new_due_date = st.date_input("Due Date", value=task["due_date"] if task["due_date"] else date.today())
            new_recurrence = st.selectbox("Recurrence", self.RECURRENCE_OPTIONS,
                                        index=self.RECURRENCE_OPTIONS.index(task["recurrence"]))
            
            # Tag input with autocomplete
            new_tags = st.multiselect("Tags", list(st.session_state.tags), default=task["tags"])
            new_tag = st.text_input("Add New Tag")
            
            if st.form_submit_button("Save Changes"):
                if new_tag:
                    new_tags.append(new_tag)
                self.edit_task(task["id"], new_title, new_description, new_category, 
                             new_due_date, new_priority, new_tags, new_recurrence)
                st.experimental_rerun()

    def process_recurring_tasks(self) -> None:
        """Process recurring tasks and create new instances if needed."""
        today = date.today()
        new_tasks = []
        
        for task in st.session_state.tasks:
            if task["completed"] and task["recurrence"] != "None":
                if task["recurrence"] == "Daily":
                    next_due = task["due_date"] + timedelta(days=1)
                elif task["recurrence"] == "Weekly":
                    next_due = task["due_date"] + timedelta(weeks=1)
                elif task["recurrence"] == "Monthly":
                    next_due = task["due_date"] + timedelta(days=30)
                
                if next_due >= today:
                    new_task = task.copy()
                    new_task["id"] = len(st.session_state.tasks) + len(new_tasks) + 1
                    new_task["completed"] = False
                    new_task["due_date"] = next_due
                    new_task["created_at"] = datetime.now()
                    new_tasks.append(new_task)
        
        st.session_state.tasks.extend(new_tasks)

def login_page():
    """Display the login page."""
    st.title("Todo List App - Login")
    
    # Create tabs for login, register, and password reset
    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Reset Password"])
    
    with tab1:
        st.subheader("Login")
        identifier = st.text_input("Username or Email", key="login_identifier")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if not identifier or not password:
                st.error("Please enter both username/email and password")
                return
            
            try:
                # Verify user credentials
                user_id = st.session_state.db.verify_user(identifier, password)
                if user_id:
                    # Get user details
                    user = st.session_state.db.get_user_by_id(user_id)
                    if user:
                        # Set session state
                        st.session_state.user_id = user_id
                        st.session_state.username = user["username"]
                        st.session_state.email = user["email"]
                        st.success("Login successful!")
                        st.rerun()  # This will trigger a rerun and show the main app
                    else:
                        st.error("User not found")
                else:
                    st.error("Invalid username/email or password")
            except Exception as e:
                st.error(f"An error occurred during login: {str(e)}")
    
    with tab2:
        st.subheader("Register")
        new_username = st.text_input("Username", key="register_username")
        new_email = st.text_input("Email", key="register_email")
        new_password = st.text_input("Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Register"):
            if not new_username or not new_email or not new_password:
                st.error("Please fill in all fields")
                return
            
            if new_password != confirm_password:
                st.error("Passwords do not match")
                return
            
            if not "@" in new_email or not "." in new_email:
                st.error("Please enter a valid email address")
                return
            
            try:
                if st.session_state.db.create_user(new_username, new_email, new_password):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Username or email already exists")
            except Exception as e:
                st.error(f"An error occurred during registration: {str(e)}")
    
    with tab3:
        st.subheader("Reset Password")
        
        # Check if we're in the reset password flow
        reset_token = st.experimental_get_query_params().get("token", [None])[0]
        
        if reset_token:
            # Show password reset form
            new_password = st.text_input("New Password", type="password", key="reset_new_password")
            confirm_password = st.text_input("Confirm New Password", type="password", key="reset_confirm_password")
            
            if st.button("Reset Password"):
                if not new_password or not confirm_password:
                    st.error("Please enter and confirm your new password")
                    return
                
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                    return
                
                try:
                    if st.session_state.db.reset_password(reset_token, new_password):
                        st.success("Password reset successful! Please login with your new password.")
                        st.experimental_set_query_params()  # Clear the token from URL
                    else:
                        st.error("Invalid or expired reset link. Please request a new one.")
                except Exception as e:
                    st.error(f"An error occurred during password reset: {str(e)}")
        else:
            # Show email input form
            email = st.text_input("Email", key="reset_email")
            
            if st.button("Send Reset Link"):
                if not email:
                    st.error("Please enter your email address")
                    return
                
                try:
                    token = st.session_state.db.create_password_reset_token(email)
                    if token:
                        # In a real app, you would send an email here
                        # For now, we'll just show the reset link
                        reset_url = f"{st.experimental_get_query_params().get('base_url', [''])[0]}/?token={token}"
                        st.success(f"Password reset link has been sent to {email}")
                        st.info(f"Reset Link: {reset_url}")
                        st.warning("Note: In a production environment, this link would be sent via email.")
                    else:
                        st.error("No account found with that email address")
                except Exception as e:
                    st.error(f"An error occurred while creating reset token: {str(e)}")

def main():
    """Main function to run the todo list application."""
    # Initialize database in session state if not already initialized
    if 'db' not in st.session_state:
        try:
            st.session_state.db = Database()
            st.success("Database initialized successfully")
        except Exception as e:
            st.error(f"Failed to initialize database: {str(e)}")
            st.stop()  # Stop the app if database initialization fails

    # Check if user is logged in
    if 'user_id' not in st.session_state:
        login_page()
        return

    # Clear the page and show the main app
    st.empty()  # Clear the login page
    
    try:
        # Get user details to ensure they still exist
        user = st.session_state.db.get_user_by_id(st.session_state.user_id)
        if not user:
            st.error("User not found. Please login again.")
            del st.session_state.user_id
            del st.session_state.username
            del st.session_state.email
            st.rerun()
            return
            
        st.title(f"Todo List App - Welcome {user['username']}!")
        
        # Add logout button
        if st.sidebar.button("Logout"):
            del st.session_state.user_id
            del st.session_state.username
            del st.session_state.email
            st.rerun()
            return

        todo_list = TodoList(st.session_state.db, st.session_state.user_id)

        # Initialize form fields in session state if they don't exist
        if 'should_clear_form' not in st.session_state:
            st.session_state.should_clear_form = False

        def clear_form():
            st.session_state.should_clear_form = True

        def get_default_value(key, default=""):
            if st.session_state.should_clear_form:
                return default
            return st.session_state.get(key, default)

        with st.sidebar:
            st.header("Add New Task")
            title = st.text_input("Task Title", value=get_default_value("form_title"))
            description = st.text_area("Task Description (optional)", value=get_default_value("form_description"))
            category = st.selectbox("Category", st.session_state.categories, 
                                  index=0 if st.session_state.should_clear_form else None)
            priority = st.selectbox("Priority", todo_list.PRIORITY_LEVELS,
                                  index=1 if st.session_state.should_clear_form else None)
            due_date = st.date_input("Due Date (optional)")
            recurrence = st.selectbox("Recurrence", todo_list.RECURRENCE_OPTIONS,
                                    index=0 if st.session_state.should_clear_form else None)
            
            # Tag input with autocomplete
            tags = st.multiselect("Select Tags", list(st.session_state.tags),
                                default=[] if st.session_state.should_clear_form else None)
            new_tag = st.text_input("Add New Tag", value=get_default_value("form_new_tag"))
            
            if st.button("Add Task"):
                if title:
                    if new_tag:
                        tags.append(new_tag)
                    todo_list.add_task(title, description, category, due_date, priority, tags, recurrence)
                    clear_form()
                    st.rerun()
                else:
                    st.error("Task title is required!")

            # Reset the clear form flag
            st.session_state.should_clear_form = False

        todo_list.view_tasks()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please try logging in again.")
        del st.session_state.user_id
        del st.session_state.username
        del st.session_state.email
        st.rerun()

if __name__ == "__main__":
    main()