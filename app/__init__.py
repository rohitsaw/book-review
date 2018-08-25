import os
from os import urandom
from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests

app = Flask(__name__)
app.secret_key= urandom(24)

# Check for environment variable
#if not os.getenv("DATABASE_URL"):
#   raise RuntimeError("DATABASE_URL is not set")

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if 'user_id' in session:
        return render_template("LogUser.html",name=session['name'])
    return render_template("index.html")

@app.route("/Registration", methods=["POST","GET"])
def Registration():
    return render_template("Registration.html")

@app.route("/Registration/Success", methods=["POST"])
def Success():
    name=request.form.get("name")
    password=request.form.get("password")
    user=db.execute("SELECT name FROM users WHERE name=:name",{"name":name}).fetchall()
    if user is None:
        db.execute("INSERT INTO users (name, password) VALUES(:name,:password)",{"name": name,"password": password})
        db.commit()
        success_review=0
        return render_template("success.html",name=name, success_review=success_review)
    else:
        error=0
        return render_template("error.html", error=error)

@app.route("/LogIN", methods=["POST", "GET"])
def LogIN():
    if 'user_id' in session:
        return render_template("LogUser.html",name=session['name'])
    return render_template("LogIN.html")

@app.route("/Loguser", methods=["POST"])
def Loguser():
    name=request.form.get("name")
    password=request.form.get("password")
    check=db.execute("SELECT id FROM users WHERE name=:name AND password=:password", {"name":name, "password":password}).fetchone()
    if check is None:
        error=1
        return render_template("error.html", error=error)
    #if session.get("check") is None:
    session['user_id']=check
    session['name']=name
    #print(session['user_id'])
    #print(session['user_id'][0])
    return render_template("LogUser.html", name=session['name'])

@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.pop('user_id',None)
    session.pop('name',None)
    return redirect(url_for('index'))

@app.route("/search", methods=["POST", "GET"])
def search():
    if 'user_id' in session:
        search=request.form.get("search")
        search='%'+search+'%'
        searchtype=request.form.get("searchtype")
        result=db.execute("SELECT * FROM books WHERE title LIKE :search or isbn LIKE :search or author LIKE :search", {"search": search}).fetchall()
        if result==[]:
            error=2
            return render_template("error.html", error=error), 404
        else:
            session.pop('book_id',None)
            return render_template("search.html",result=result,searchtype=searchtype)
    else:
        return redirect(url_for('LogIN'))

@app.route("/book/<string:book>", methods=["GET", "POST"])
def book(book):
    if 'user_id' in session:
        show=db.execute("SELECT * FROM books WHERE isbn LIKE :isbn", {"isbn": book}).fetchall()
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "D0u9FnMqeQLlpYXTmCNBA", "isbns": show[0].isbn})
        if res.status_code!=200:
            raise Exception("ERROR: request unsuccessfull")
        data=res.json()
        no_of_rating=data["books"][0]["work_ratings_count"]
        avg_rating=data["books"][0]["average_rating"]
        session['book_id']=show[0].isbn
        result=db.execute("SELECT * FROM reviews WHERE user_id LIKE :user_id and book_id LIKE :book_id",{"user_id": str(session['user_id'][0]), "book_id": session['book_id']}).fetchall()
        if result==[]:
            return render_template("book.html",book=show,no_of_rating=no_of_rating,avg_rating=avg_rating,flag=0)
        else:
            return render_template("book.html",book=show,no_of_rating=no_of_rating,avg_rating=avg_rating,flag=1,text=result[0][2], range=result[0][3])
    else:
        return redirect(url_for('LogIN'))

@app.route("/review", methods=["POST"])
def review():
    if 'user_id' in session:
        result=db.execute("SELECT * FROM reviews WHERE user_id LIKE :user_id and book_id LIKE :book_id",{"user_id": str(session['user_id'][0]), "book_id": session['book_id']}).fetchall()
        if result==[]:
            text=request.form.get("text")
            range=request.form.get("rating")
            db.execute("INSERT INTO reviews (user_id, book_id, text_review, point_review) VALUES(:user_id, :book_id, :text_review, :point_review)",{"user_id":session['user_id'][0], "book_id":session['book_id'], "text_review":text, "point_review": range})
            db.commit()
            success_review=1
            return render_template("success.html", name=session['name'], success_review=success_review)
        else:
            error=4
            return render_template("error.html", error=error )
    else:
        return redirect(url_for('LogIN'))


@app.route("/api/<string:isbn>")
def api(isbn):
    flag=db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchall()
    if flag==[]:
        return jsonify({"error": "Invalid ISBN Number"}), 404
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "D0u9FnMqeQLlpYXTmCNBA", "isbns": isbn})
    if res.status_code!=200:
        raise Exception("ERROR: request unsuccessfull")
    data=res.json()
    no_of_rating=data["books"][0]["work_ratings_count"]
    avg_rating=data["books"][0]["average_rating"]
    return jsonify({
        "title": flag[0].title,
        "author": flag[0].author,
        "year": flag[0].pyear,
        "isbn": isbn,
        "review_count": no_of_rating,
        "average_score": avg_rating
        })
