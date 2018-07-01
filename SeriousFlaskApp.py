from functools import wraps

from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from data import article
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt

app = Flask(__name__)

# config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'flask_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# initialize
mysql = MySQL(app)


# Articles = article()


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/article')
def article():
    # create cursor
    cur = mysql.connection.cursor()

    # get articles
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = "You have no posts,Add some"
        return render_template('articles.html', msg=msg)
    # close connection
    cur.close()


@app.route('/detail/<string:id>/')
def detail(id):
    # create cursor
    cur = mysql.connection.cursor()

    # get articles
    result = cur.execute("SELECT * FROM articles WHERE id = %s" % id)
    articles = cur.fetchone()
    return render_template('detail.html', articles=articles)


# register WTF forms
class RegisterForm(Form):
    name = StringField('Name', [validators.length(min=1, max=50)])
    username = StringField('Username', [validators.length(min=4, max=25)])
    email = StringField('Email', [validators.length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('confirm Password')


# register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        # create cursor

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users( name,email,username,password) VALUES(%s, %s, %s, %s)",
                    (name, email, username, password))

        # commit
        mysql.connection.commit()

        # close connection

        cur.close()
        flash("You are now registered and can login", 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# user Login

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        # get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        cur = mysql.connection.cursor()
        # Get user by username

        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password = data['password']

            # compare passwords

            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in as %s' % username, 'success')

                return redirect(url_for('dashboard'))
                cur.close()
            else:
                error = 'Invalid password'
                return render_template('login.html', error=error)

        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorised page,please login', 'danger')
            return redirect(url_for('login'))

    return wrap


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are logged out', 'success')
    return redirect(url_for('login'))


# dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    cur = mysql.connection.cursor()

    # get articles
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = "You have no posts,Add some"
        return render_template('dashboard.html', msg=msg)
    # close connection
    cur.close()


# add article
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=255)])
    body = TextAreaField('Body', [validators.Length(min=30)])


# create articl
@app.route('/add_article', methods=['POST', 'GET'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # create cursor

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title,body,author) VALUES (%s,%s, %s)", (title, body, session['username']))

        # commit

        mysql.connection.commit()

        # close
        cur.close()
        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['POST', 'GET'])
@is_logged_in
def edit_article(id):
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles WHERE id = %s" % id)
    article = cur.fetchone()
    form = ArticleForm(request.form)

    # populate fields

    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # create cursor


        cur.execute("UPDATE articles SET title = %s, body=%s WHERE id = %s", [title, body, id])

        # commit

        mysql.connection.commit()

        # close
        cur.close()
        flash('Article updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    # commit

    mysql.connection.commit()

    # close
    cur.close()
    flash('Article deleted', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
