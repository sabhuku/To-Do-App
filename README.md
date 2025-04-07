# Todo List App

A feature-rich todo list application built with Streamlit.

## Features
- Add, edit, and delete tasks
- Set task priorities (High, Medium, Low)
- Add categories and tags
- Set due dates
- Recurring tasks
- Task filtering and sorting
- Search functionality

## Local Development
1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run todo_app_streamlit.py
   ```

## Deployment Options

### Option 1: Streamlit Cloud (Recommended)
1. Create an account on [Streamlit Cloud](https://streamlit.io/cloud)
2. Connect your GitHub repository
3. Deploy your app with one click

### Option 2: Heroku
1. Create a `Procfile`:
   ```
   web: streamlit run todo_app_streamlit.py
   ```
2. Create a `setup.sh`:
   ```bash
   mkdir -p ~/.streamlit/
   echo "\
   [server]\n\
   headless = true\n\
   port = $PORT\n\
   enableCORS = false\n\
   \n\
   " > ~/.streamlit/config.toml
   ```
3. Deploy to Heroku using their CLI or dashboard

### Option 3: PythonAnywhere
1. Create an account on [PythonAnywhere](https://www.pythonanywhere.com/)
2. Upload your files
3. Set up a web app using the WSGI configuration file

## Data Storage
The app currently stores data in Streamlit's session state. For production use, consider:
- Adding a database (SQLite, PostgreSQL, etc.)
- Implementing user authentication
- Adding data persistence 