from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'mysecret'  # You can change this to anything random

# Initialize DB
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, gender TEXT, age INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS registrations (user_id INTEGER, course_id INTEGER)''')
    conn.commit()

    # Add sample courses
    cursor.execute("SELECT COUNT(*) FROM courses")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO courses (name) VALUES (?)", [
            ("Python Basics",),
            ("Web Development",),
            ("Data Science",)
        ])
        conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        gender = request.form['gender']
        age = int(request.form['age'])
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, gender, age) VALUES (?, ?, ?, ?)", (username, password, gender, age))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials"
    return render_template("login.html")

@app.route('/admin_login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        if username == "admin" and password == "admin123":
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid admin credentials"
    return render_template("admin_login.html")

@app.route('/admin_dashboard', methods=["GET", "POST"])
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Handle filtering by gender, age, and courses
    gender_filter = request.form.get('gender') if request.method == "POST" else None
    age_filter = request.form.get('age') if request.method == "POST" else None
    course_filter = request.form.get('course') if request.method == "POST" else None

    # Base query to fetch users
    query = """
        SELECT DISTINCT u.id, u.username, u.password, u.gender, u.age
        FROM users u
        LEFT JOIN registrations r ON u.id = r.user_id
        LEFT JOIN courses c ON r.course_id = c.id
        WHERE 1=1
    """
    params = []

    # Apply gender filter
    if gender_filter and gender_filter != "All":
        query += " AND u.gender = ?"
        params.append(gender_filter)

    # Apply age filter
    if age_filter and age_filter != "All":
        if age_filter == "18-25":
            query += " AND u.age BETWEEN 18 AND 25"
        elif age_filter == "25-30":
            query += " AND u.age BETWEEN 25 AND 30"
        elif age_filter == "30+":
            query += " AND u.age > 30"

    # Apply course filter
    if course_filter and course_filter != "All":
        # Subquery to count courses per user
        subquery = """
            SELECT user_id, COUNT(*) as course_count, GROUP_CONCAT(c.name) as course_names
            FROM registrations r
            JOIN courses c ON r.course_id = c.id
            GROUP BY user_id
        """
        query += f" AND u.id IN (SELECT user_id FROM ({subquery}) WHERE "
        
        if course_filter == "Python Basics Only":
            query += "course_count = 1 AND course_names = 'Python Basics')"
        elif course_filter == "Web Development Only":
            query += "course_count = 1 AND course_names = 'Web Development')"
        elif course_filter == "Data Science Only":
            query += "course_count = 1 AND course_names = 'Data Science')"
        elif course_filter == "Python Basics & Web Development":
            query += "course_count = 2 AND course_names = 'Python Basics,Web Development')"
        elif course_filter == "Python Basics & Data Science":
            query += "course_count = 2 AND course_names = 'Python Basics,Data Science')"
        elif course_filter == "Web Development & Data Science":
            query += "course_count = 2 AND course_names = 'Web Development,Data Science')"

    cursor.execute(query, params)
    users = cursor.fetchall()

    # Fetch courses for each user to display
    user_courses = {}
    for user in users:
        user_id = user[0]
        cursor.execute("""
            SELECT c.name
            FROM registrations r
            JOIN courses c ON r.course_id = c.id
            WHERE r.user_id = ?
        """, (user_id,))
        courses = [row[0] for row in cursor.fetchall()]
        user_courses[user_id] = courses

    conn.close()
    return render_template("admin_dashboard.html", users=users, user_courses=user_courses, 
                         selected_gender=gender_filter, selected_age=age_filter, selected_course=course_filter)

@app.route('/clear_database')
def clear_database():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM registrations")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='users'")  # Reset the auto-increment ID for users
    conn.commit()
    conn.close()
    return "Database cleared! <a href='/'>Go back to home</a>"

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()
    conn.close()
    return render_template("dashboard.html", courses=courses)

@app.route('/register_course/<int:course_id>', methods=["POST"])
def register_course(course_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registrations WHERE user_id = ? AND course_id = ?", (user_id, course_id))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO registrations (user_id, course_id) VALUES (?, ?)", (user_id, course_id))
        conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/my_courses')
def my_courses():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT courses.name FROM courses
        JOIN registrations ON courses.id = registrations.course_id
        WHERE registrations.user_id = ?
    ''', (user_id,))
    courses = cursor.fetchall()
    conn.close()
    return render_template("my_courses.html", courses=courses)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)