import streamlit as st
from typing import List, Dict, Set, Optional
from datetime import datetime, date, timedelta
import json
import traceback
from database import Database
import logging

logger = logging.getLogger(__name__)

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
            # Reload tasks from the database
            st.session_state.tasks = self.db.get_tasks(self.user_id)
        else:
            st.error("Failed to add task.")

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
        # Debugging: Check the structure of the task
        task = next((t for t in st.session_state.tasks if t["id"] == task_id), None)
        if task is None:
            st.error(f"Task with ID {task_id} not found in session state.")
            return

        task_data = {"completed": True}
        if self.db.update_task(task_id, self.user_id, task_data):
            # Update session state immediately for responsiveness
            for task in st.session_state.tasks:
                if task['id'] == task_id:
                    task['completed'] = task_data["completed"]
                    break
            logger.info(f"Task {task_id} status toggled to {task_data['completed']}")
            # No explicit rerun needed, on_change handles it
        else:
            st.error(f"Failed to update task {task_id}.")

    def delete_task(self, task_id: int) -> None:
        """Delete a task from the todo list."""
        if self.db.delete_task(task_id, self.user_id):
            st.success(f"Task {task_id} deleted successfully!")
            # Update the session state directly
            st.session_state.tasks = self.db.get_tasks(self.user_id)
        else:
            st.error(f"Task with ID {task_id} not found.")

    def toggle_task_completion(self, task_id: int, current_status: bool):
        """Toggle the completion status of a task."""
        new_status = not current_status
        task_data = {"completed": new_status}
        logger.debug(f"Toggling task {task_id} completion from {current_status} to {new_status}")
        if self.db.update_task(task_id, self.user_id, task_data):
            # Update session state immediately for responsiveness
            for task in st.session_state.tasks:
                if task['id'] == task_id:
                    task['completed'] = new_status
                    logger.debug(f"Session state updated for task {task_id}")
                    break
            logger.info(f"Task {task_id} status toggled to {new_status}")
            # Streamlit reruns automatically due to widget interaction (on_change)
        else:
            st.error(f"Failed to update task {task_id} status.")

    def view_tasks(self) -> None:
        """Display all tasks in the todo list with filtering and sorting."""
        # --- Get All Tasks ---
        tasks = self.db.get_tasks(self.user_id) # Fetch all tasks first

        st.subheader("Filter & Sort Tasks")

        # Initialize filter/sort options
        categories = ["All"]
        priorities = ["All", "High", "Medium", "Low"]
        statuses = ["All", "Active", "Completed"]
        sort_options = ["Due Date", "Priority", "Title"]

        if tasks:
            # Dynamically get categories from existing tasks
            task_categories = set(task.get('category', 'Uncategorized') for task in tasks if task.get('category'))
            categories.extend(sorted(list(task_categories)))
        else:
             st.info("No tasks yet! Add one using the form above.")
             # Don't show filters if there are no tasks
             return # Exit the function early


        col1, col2, col3, col4 = st.columns(4)
        with col1:
            selected_category = st.selectbox("Category:", categories, key="filter_category")
        with col2:
            selected_priority = st.selectbox("Priority:", priorities, key="filter_priority")
        with col3:
            # Use index=1 to default to "Active" tasks initially
            selected_status = st.radio("Status:", statuses, index=1, horizontal=True, key="filter_status")
        with col4:
            selected_sort = st.selectbox("Sort by:", sort_options, key="sort_tasks")

        # --- Filtering ---
        filtered_tasks = tasks # Start with all tasks
        if selected_category != "All":
            filtered_tasks = [task for task in filtered_tasks if task.get('category') == selected_category]
        if selected_priority != "All":
            filtered_tasks = [task for task in filtered_tasks if task.get('priority') == selected_priority]
        if selected_status == "Active":
            filtered_tasks = [task for task in filtered_tasks if not task.get('completed')]
        elif selected_status == "Completed":
            filtered_tasks = [task for task in filtered_tasks if task.get('completed')]

        # --- Sorting ---
        priority_map = {"High": 0, "Medium": 1, "Low": 2}
        # Define a very large date for sorting tasks without due dates last
        far_future_date = date(9999, 12, 31)

        def get_sort_key(task):
            if selected_sort == "Due Date":
                due_date_str = task.get("due_date")
                if due_date_str:
                    try:
                        # Convert string date from DB to date object for comparison
                        return datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        # Handle potential invalid date strings or types gracefully
                        logger.warning(f"Invalid date format for task {task.get('id')}: {due_date_str}")
                        return far_future_date # Sort invalid dates last
                else:
                    return far_future_date # Sort tasks without due dates last
            elif selected_sort == "Priority":
                return priority_map.get(task.get("priority"), 3) # Default to lowest prio if missing
            elif selected_sort == "Title":
                return task.get("title", "").lower() # Sort case-insensitively, handle missing title
            return task.get("id") # Default sort by ID if needed

        # Handle potential errors during sorting key access
        try:
            sorted_tasks = sorted(filtered_tasks, key=get_sort_key)
        except Exception as e:
            logger.error(f"Error during task sorting: {e}")
            st.error("An error occurred while sorting tasks.")
            sorted_tasks = filtered_tasks # Show unsorted list on error

        # --- Display Tasks ---
        st.markdown("---") # Separator
        if not sorted_tasks:
            st.info("No tasks match the current filters.")
        else:
            # Use singular 'task' if only one task matches
            task_count_text = f"{len(sorted_tasks)} task"
            if len(sorted_tasks) != 1:
                task_count_text += "s"
            st.write(f"Displaying {task_count_text}:")

            for task in sorted_tasks:
                 # We need to wrap the display_task call in a try-except
                 # because errors in display_task could stop the loop
                 try:
                    # Pass the task dictionary to the display method
                    self.display_task(task)
                 except Exception as e:
                    logger.error(f"Error displaying task {task.get('id', 'N/A')}: {e}", exc_info=True)
                    st.error(f"Error displaying task {task.get('id', 'N/A')}. Check logs.")

    def show_calendar_view(self, tasks: List[Dict]) -> None:
        """Display tasks in a calendar view."""
        from datetime import datetime, timedelta
        import calendar
        
        # Get current month and year
        today = datetime.now().date()
        if 'current_month' not in st.session_state:
            st.session_state.current_month = today.month
        if 'current_year' not in st.session_state:
            st.session_state.current_year = today.year
        
        # Use session state for navigation
        if st.button("Previous Month"):
            if st.session_state.current_month == 1:
                st.session_state.current_month = 12
                st.session_state.current_year -= 1
            else:
                st.session_state.current_month -= 1

        if st.button("Next Month"):
            if st.session_state.current_month == 12:
                st.session_state.current_month = 1
                st.session_state.current_year += 1
            else:
                st.session_state.current_month += 1
        
        # Create month navigation
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader(f"{calendar.month_name[st.session_state.current_month]} {st.session_state.current_year}")
        
        # Get the calendar for the current month
        cal = calendar.monthcalendar(st.session_state.current_year, st.session_state.current_month)
        
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
                
                current_date = datetime(st.session_state.current_year, st.session_state.current_month, day).date()
                day_tasks = [task for task in tasks if task["due_date"] == current_date]
                
                if day_tasks:
                    with cols[i].expander(f"{day} ({len(day_tasks)})"):
                        for task in day_tasks:
                            self.display_task(task)
                else:
                    cols[i].write(day)

    def show_list_view(self, tasks: List[Dict], sort_by: str) -> None:
        """Display tasks in a list view with filtering and sorting."""
        # Sort tasks based on the selected sorting method
        if sort_by == "Due Date":
            tasks.sort(key=lambda x: (x["due_date"] is None, x["due_date"] or datetime.max.date()))
        elif sort_by == "Priority":
            priority_order = {"High": 0, "Medium": 1, "Low": 2}
            tasks.sort(key=lambda x: priority_order[x["priority"]])
        else:  # Created Date
            tasks.sort(key=lambda x: x.get("created_at", datetime.max))

        st.subheader("=== Todo List ===")
        for task in tasks:
            self.display_task(task)

    def display_task(self, task: Dict) -> None:
        """Display a single task with due date styling."""
        required_keys = {"id", "title", "description", "category", "due_date", "priority", "tags", "completed"}
        if not required_keys.issubset(task.keys()):
            st.error(f"Task {task.get('id', 'Unknown')} is missing required fields.")
            return

        # Validate due_date
        due_date = task.get("due_date") # Use .get for safety
        if due_date is not None and not isinstance(due_date, date):
            st.error(f"Task {task['id']} has an invalid due_date: {due_date} (Type: {type(due_date)})")
            # We might want to try converting if it's a string, but view_tasks should handle this.
            # For display, if it's not a date or None after view_tasks, it's an error.
            return # Stop displaying this task if date is invalid

        col1, col2, col3 = st.columns([1, 10, 1])

        with col1:
            # Use unique keys for each button based on task ID and action
            complete_key = f"complete_{task['id']}"
            delete_key = f"delete_{task['id']}"

            # Always display the checkbox; its 'value' determines checked/unchecked state
            is_completed = st.checkbox(
                f"Complete task {task['id']}",  # Add descriptive label
                value=task["completed"],
                key=f"complete_{task['id']}",
                on_change=self.toggle_task_completion, # Ensure correct callback
                args=(task['id'], task["completed"]), # Pass ID and current status
                help="Mark as Incomplete" if task["completed"] else "Mark as Complete", # Added tooltip
                label_visibility="collapsed" # Hide the label visually
            )

            if st.button("🗑️", key=delete_key, help="Delete task", use_container_width=True):
                self.delete_task(task['id'])

        with col2:
            priority_icon_map = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
            priority_icon = priority_icon_map.get(task["priority"], "⚪️") # Safely get icon, default to white circle
            due_date_style = self._get_due_date_style(due_date, task["completed"]) # Use validated due_date
            title_style = "text-decoration: line-through;" if task["completed"] else ""

            st.markdown(f"{priority_icon} <span style='{title_style}'>{task['title']}</span>", unsafe_allow_html=True)
            if task["description"]:
                st.markdown(f"*{task['description']}*")
            st.markdown(f"**Category:** {task['category']} | **Priority:** {task['priority']}")
            if task["due_date"]:
                st.markdown(f"<span class='{due_date_style}'>Due: {task['due_date']}</span>", unsafe_allow_html=True)
            if task["tags"]:
                st.markdown(f"**Tags:** {', '.join(task['tags'])}")

        with col3:
            edit_key = f"edit_{task['id']}"
            if st.button("✏️", key=edit_key, help="Edit task", use_container_width=True):
                st.session_state.editing_task_id = task['id']
                st.rerun() # Rerun to display the form immediately

        # Show edit form BELOW the columns if this task is being edited
        if st.session_state.get("editing_task_id") == task["id"]:
            self.show_edit_form(task)

    def _get_due_date_style(self, due_date: Optional[date], completed: bool) -> str:
        """Return CSS style for due date based on urgency."""
        # Check if due_date is valid before calculating style
        if due_date is None:
            return "" # No style for None
        elif isinstance(due_date, date):
            pass # Valid date object
        else:
            # If it's not None or date, something is wrong (conversion should have happened)
            st.error(f"Invalid due_date type for styling: {type(due_date)}")
            return "" # Return empty style on error

        today = date.today()
        delta = (due_date - today).days
        
        if completed:
            return ""
        elif delta < 0:
            return "color: #ff4b4b; font-weight: bold;"  # Overdue
        elif delta == 0:
            return "color: #ffa500; font-weight: bold;"  # Due today
        elif delta <= 3:
            return "color: #f4c430;"  # Due soon
        return ""

    def show_edit_form(self, task: Dict) -> None:
        """Show form to edit a task."""
        with st.form(key=f"edit_task_{task['id']}"):
            new_title = st.text_input("Title", value=task["title"])
            new_description = st.text_area("Description", value=task.get("description", ""))
            new_category = st.text_input("Category", value=task.get("category", ""))
            current_priority = task["priority"]
            default_priority_index = 0 # Default to first item
            if current_priority in self.PRIORITY_LEVELS:
                default_priority_index = self.PRIORITY_LEVELS.index(current_priority)
            elif "Medium" in self.PRIORITY_LEVELS: # Fallback to Medium if possible
                default_priority_index = self.PRIORITY_LEVELS.index("Medium")

            new_priority = st.selectbox("Priority", options=self.PRIORITY_LEVELS, index=default_priority_index)

            # Get current due date, handle None
            current_due_date = task.get("due_date")
            new_due_date = st.date_input("Due Date (optional)", value=current_due_date if isinstance(current_due_date, date) else None)

            # Safely get recurrence, defaulting to 'None' if not present
            current_recurrence = task.get('recurrence', 'None')
            # Ensure the default value exists in the options before finding the index
            try:
                recurrence_index = self.RECURRENCE_OPTIONS.index(current_recurrence)
            except ValueError:
                st.warning(f"Recurrence value '{current_recurrence}' not in options. Defaulting to 'None'.")
                recurrence_index = self.RECURRENCE_OPTIONS.index('None') # Default to 'None'

            new_recurrence = st.selectbox(
                "Recurrence", 
                options=self.RECURRENCE_OPTIONS, 
                index=recurrence_index
            ) 
            new_tags = st.text_input("Tags (comma-separated)", value=", ".join(task.get("tags", [])), key=f"tags_{task['id']}")

            submit_button = st.form_submit_button("Update Task")
            if submit_button:
                if new_tags:
                    tags = [tag.strip() for tag in new_tags.split(",")]
                else:
                    tags = []
                self.edit_task(
                    task["id"],
                    new_title,
                    new_description,
                    new_category,
                    new_due_date,
                    new_priority,
                    tags,
                    new_recurrence
                )
                # Update tasks in session state
                st.session_state.tasks = self.db.get_tasks(self.user_id)
                # Clear editing state
                st.session_state.editing_task_id = None

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

    def get_tasks(self, user_id: int) -> List[Dict]:
        tasks = self.db.get_tasks(user_id)
        # Perform type logging for debugging
        logger.debug(f"Retrieved tasks for user {user_id}: {tasks}")
        for task in tasks:
            for key, value in task.items():
                logger.debug(f"Task ID: {task['id']}, Field: {key}, Type: {type(value)}")
            # Date conversion is now handled reliably in view_tasks
        return tasks

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
                        st.session_state.authenticated = True
                        st.success("Login successful!")
                        st.rerun()  # Trigger a rerun to immediately reflect the login
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
        reset_token = st.query_params.get("token", [None])[0]
        
        if reset_token:
            # Show password reset form
            new_password = st.text_input("New Password", type="password", key="reset_new_password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
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
                        st.set_query_params()  # Clear the token from URL
                        st.info("If the reset link is still visible, please refresh the page.")
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
                        reset_url = f"{st.query_params.get('base_url', [''])[0]}/?token={token}"
                        st.success(f"Password reset link has been sent to {email}")
                        st.info(f"Reset Link: {reset_url}")
                        st.warning("Note: In a production environment, this link would be sent via email.")
                    else:
                        st.error("No account found with that email address")
                except Exception as e:
                    st.error(f"An error occurred while creating reset token: {str(e)}")

def main():
    st.session_state.setdefault("filter_show_completed", True)

    """Main function to run the todo list application."""
    # Initialize database in session state if not already initialized
    if 'db' not in st.session_state:
        try:
            st.session_state.db = Database()
            st.success("Database initialized successfully")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please try again.")
            st.stop()

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'tasks' not in st.session_state:
        st.session_state.tasks = []
    if 'editing_task_id' not in st.session_state:
        st.session_state.editing_task_id = None

    # Check if user is logged in
    if not st.session_state.authenticated:
        login_page()
        return

    # Main app content
    try:
        # Get user details to ensure they still exist
        user = st.session_state.db.get_user_by_id(st.session_state.user_id)
        if not user:
            st.error("User not found. Please login again.")
            st.session_state.authenticated = False
            st.session_state.pop('user_id', None)
            st.session_state.pop('username', None)
            st.session_state.pop('email', None)
            return
            
        st.title(f"Todo List App - Welcome {user['username']}!")
        
        # Add logout button
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.pop('user_id', None)
            st.session_state.pop('username', None)
            st.session_state.pop('email', None)
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
                else:
                    st.error("Task title is required!")

            # Reset the clear form flag
            st.session_state.should_clear_form = False

        todo_list.view_tasks()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check the console for detailed error information.")
        traceback.print_exc()
        # Keep the logout logic if needed, or comment it out during debugging
        st.session_state.authenticated = False
        st.session_state.pop('user_id', None)
        st.session_state.pop('username', None)
        st.session_state.pop('email', None)

if __name__ == "__main__":
    main()