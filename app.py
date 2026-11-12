from flask import Flask, render_template, request, url_for, redirect, flash, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
import datetime
import random
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = "abc123"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "tester"
app.config["MYSQL_PASSWORD"] = "123456"
app.config["MYSQL_DB"] = "cms"

app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')

mysql = MySQL(app)
'''
def update_password():
    hashed_pwd = generate_password_hash("123456")
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET password = %s WHERE id = 1", (hashed_pwd,))
    mysql.connection.commit()
    cur.close()
'''
def get_user_by_username(username):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, password FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    if row:
        return {'id':row[0], 'username':row[1], 'password_hash':row[2]}
    return None

def add_post(title, description, date, filename, price):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO content (title, description, media, publish, price) VALUES (%s, %s, %s, %s, %s)", (title, description, filename, date, price))
    mysql.connection.commit()
    cur.close()

def edit_post(id, title, description, date, newname, price):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE content SET title = %s, description = %s, media = %s, publish = %s, price =%s WHERE id = %s", (title, description, newname, date, price, id))
    mysql.connection.commit()
    cur.close()

def delete_post(post_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE content SET status = 0 WHERE id = %s", (post_id,))
    mysql.connection.commit()
    cur.close()

def recovery_post(post_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE content SET status = 1 WHERE id = %s", (post_id,))
    mysql.connection.commit()
    cur.close()

def search_posts(search):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM content WHERE title LIKE %s OR description LIKE %s AND status > 0", (f"%{search}%", f"%{search}%"))
    rows = cur.fetchall()
    cur.close()
    return rows

def get_content():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM content WHERE status > 0")
    rows = cur.fetchall()
    cur.close()
    return rows

def get_posts(page):
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM content WHERE status > 0")
    res = cur.fetchone()[0]
    count = res//9
    if res%9 > 0:
        count+=1
    pn = (page-1)*9
    cur.execute("SELECT * FROM content WHERE status > 0 LIMIT 9 OFFSET %s", (pn,))
    rows = cur.fetchall()
    cur.close()
    return rows, count

def get_post(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM content WHERE id = %s", (id,))
    rows = cur.fetchone()
    cur.close()
    return rows

def get_archive():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM content WHERE status = 0")
    rows = cur.fetchall()
    cur.close()
    return rows

def generate_filename(filename):
    ext = filename.split('.')[-1]
    s = "qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
    res = ""
    for i in range(16):
        res += s[random.randint(0,51)]
    return res+"."+ext

@app.route('/')
def index():
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    posts, count = get_posts(page)
    return render_template('index.html', posts=posts, count=count)

@app.route('/search', methods=["POST", "GET"])
def search():
    if request.method == "POST":
        title = request.form.get('search')
        res = search_posts(title)
        return render_template('index.html', posts=res)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=["POST", "GET"])
def login():
    
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('admin'))
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin', methods=["POST", "GET"])
def admin():
    if 'user_id' not in session:
        flash("Требуется авторизация")
        return redirect(url_for('login'))

    if request.method == "POST":
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        file = request.files['file']
        price = request.form.get('price')
        if file and file.filename:
            newname = generate_filename(file.filename)
            user_dir = os.path.join(app.config["UPLOAD_FOLDER"])

            file_path = os.path.join(user_dir, newname)
            file.save(file_path)

            add_post(title, description, date, newname, price)
            flash("Файл загружен")

    posts = get_content()
    archive = get_archive()
    date = datetime.date.today()
    return render_template('cms.html', posts=posts, date=date, archive=archive)

@app.route('/page/<id>')
def page(id):
    post = get_post(id)
    return render_template('page.html', post=post)

@app.route('/edit/<id>', methods=["POST", "GET"])
def edit(id):
    if request.method == "POST":
        title = request.form.get('title')
        description = request.form.get('description')
        date = request.form.get('date')
        file = request.files['file']
        price = request.form.get('price')
        current_file = request.form.get('current_file')
        if file and file.filename:
            user_dir = os.path.join(app.config["UPLOAD_FOLDER"])
            file_path = os.path.join(user_dir, current_file)
            os.remove(file_path)

            newname = generate_filename(file.filename)
            file_path = os.path.join(user_dir, newname)
            file.save(file_path)
        else:
            newname = current_file
        edit_post(id, title, description, date, newname, price)
        return redirect(url_for('admin'))
            
    post = get_post(id)
    return render_template('edit.html', post=post)

@app.route('/delete/<id>')
def delete(id):
    delete_post(id)
    return redirect(url_for('admin'))

@app.route('/recovery/<id>')
def recovery(id):
    recovery_post(id)
    return redirect(url_for('admin'))