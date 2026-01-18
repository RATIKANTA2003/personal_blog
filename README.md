🚀 Personal Blog Application
A clean and functional blog application built using Python and the Flask web framework. This project allows users to view posts, while providing an organized structure for templates and static assets.

🛠️ Tech Stack
Backend: Python (Flask)

Frontend: HTML5, CSS3 (Jinja2 Templates)

Database: SQLite (indicated by the instance folder)

✨ Features
Dynamic Routing: Easily navigate between different blog posts.

Responsive Design: Styled using custom CSS for mobile and desktop views.

Database Integration: Stores blog content securely in a local instance.

📂 Project Structure
Plaintext

├── instance/        # SQLite database files
├── static/          # CSS, images, and JavaScript
├── templates/       # HTML files (base, index, post, etc.)
├── app.py           # Main Flask application entry point
└── README.md        # Project documentation
⚙️ Getting Started
1. Clone the repository
Bash

git clone https://github.com/RATIKANTA2003/personal_blog.git
cd personal_blog
2. Set up a Virtual Environment (Recommended)
Bash

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
3. Install Dependencies
(Note: You should create a requirements.txt file, but for now:)

Bash

pip install flask
4. Run the App
Bash

python app.py
Visit http://127.0.0.1:5000 in your browser.
