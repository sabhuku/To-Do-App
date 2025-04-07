# Todo App with User Authentication

A Streamlit-based todo application with user authentication and database support.

## Features
- User registration and login
- Task management (add, edit, delete, mark as complete)
- Priority levels and due dates
- Categories and tags
- Persistent storage using SQLite

## Deployment Instructions

### Deploying to Streamlit Cloud

1. Create a GitHub repository and push your code:
   ```bash
   git init
   git add .
   git commit -r "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository
   - Set the main file path to `todo_app_streamlit.py`
   - Click "Deploy"

3. Once deployed, you'll get a URL like `https://your-app-name.streamlit.app`
   - Share this URL with other users
   - They can register and use the app

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   streamlit run todo_app_streamlit.py
   ```

## Security Notes
- Passwords are hashed using SHA-256
- Each user's data is isolated
- No sensitive data is stored in plain text

## Support
If you encounter any issues, please check the Streamlit documentation or create an issue in the GitHub repository. 