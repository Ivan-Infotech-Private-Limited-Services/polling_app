from flask import Flask, current_app, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import re
from authlib.integrations.flask_client import OAuth
from datetime import datetime
from api_key import *

app = Flask(__name__)
app.secret_key = "Tom"
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id = Client_ID,
    client_secret = Client_Secret,
    server_metadata_uri="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={'scope':'openid profile email'}
)

#Configure SQL Alchemy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///polling_app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

#Database model
class User(db.Model):
    #Class Variable
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Question(db.Model):
    #Class Variable
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(1000), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id') )
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"{self.text} created by {self.creator_id}"
    
    def get_options(self):
        return Option.query.filter_by(question_id=self.id).all()
    
    def get_user(self):
        return User.query.get(self.creator_id)
    
    def get_answers(self):
        return Answer.query.filter_by(question_id=self.id).all()

class Option(db.Model):
    #Class Variable
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(10000), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    vote_count = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    date_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def vote(self):
        self.vote_count += 1
        db.session.commit()
    
    def __repr__(self):
        return f"{self.text} in question {self.question_id}"
    
    def get_question(self):
        return Question.query.get(self.question_id)
    
    def get_answers(self):
        return Answer.query.filter_by(question_id=self.question_id, option_id=self.id).all()
    
    def get_user(self):
        return User.query.get(self.user_id)

class Answer(db.Model):
    #Class Variable
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'))
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    date_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"{self.user_id} answered {self.question_id} with {self.option_id}"
    
    def get_question(self):
        return Question.query.get(self.question_id)
    
    def get_option(self):
        return Option.query.get(self.option_id)
    
    def get_user(self):
        return User.query.get(self.user_id)

#routes
################################################################
#home
@app.route("/", methods=["GET","POST"])
def home():
    if "username" in session and 'loggedin' in session:
        print(current_app.config['MAX_CONTENT_LENGTH'])
        return redirect(url_for('dashboard'))
    else:
        return render_template("index.html", loggedin=False)

#Login
@app.route("/login", methods=["GET","POST"])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
          session['loggedin'] = True
          session['id'] = user.id
          session["username"] = username
          return redirect(url_for('dashboard'))
        else:
            msg = ("Invalid Username or Password")
            return render_template("index.html", error=msg)
    else:
         return render_template("index.html")

#Register
@app.route("/register", methods=["POST", "GET"])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        email = request.form['email']
        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        user = User.query.filter_by(username=username).first()
        if user:
            msg = ("Username already exists!")
            return render_template("register.html", error= msg )
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg =('Invalid email format!')
            return render_template("register.html", error= msg )
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = ('Username must contain only characters and numbers!')
            return render_template("register.html", error= msg )
        elif not re.match(password_regex, password):
            msg =  (('Password must be at least 8 characters long, contain at least one uppercase letter, '
                'one lowercase letter, one number, and one special character (@, $, !, %, *, ?, &).'))
            return render_template("register.html", error= msg )
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            session["username"] = username
            session['loggedin'] = True
            session['id'] = new_user.id
            return redirect(url_for('dashboard'))
    else:
        msg = ''
    return render_template('register.html')

#Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html", username=session["username"], loggedin=True)
    else:
        return redirect(url_for('home'))

#Logout
@app.route("/logout")
def logout():
    session.clear()
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop("username", None)
    return redirect(url_for('home'))

#Question Listing
@app.route("/questions")
def questions():
    if 'loggedin' in session:
        question_list = Question.query.all()
        users = User.query.all()
        db.session.commit()
        if users:
            return render_template("questions.html", question_list=question_list, username=session["username"], loggedin=True)
    else:
        msg = ("Please enter a username and password")
        return render_template("index.html", error=msg)

#Question Creation
@app.route("/create_question", methods=["POST", "GET"])
def create_question():
    if request.method == 'POST':
        if "username" in session:
            question_text = request.form["question_text"]
            new_question = Question(text=question_text, creator_id=session["id"], time_created=datetime.now(), time_updated = datetime.now())
            db.session.add(new_question)
            db.session.commit()
            db.session.refresh(new_question)
            option_text1 = request.form["option_text1"]
            option_text2 = request.form["option_text2"]
            option_text3 = request.form["option_text3"]
            option_text4 = request.form["option_text4"]
            new_option1 = Option(text=option_text1, question_id=new_question.id)
            new_option2 = Option(text=option_text2, question_id=new_question.id)
            new_option3 = Option(text=option_text3, question_id=new_question.id)
            new_option4 = Option(text=option_text4, question_id=new_question.id)
            db.session.add(new_option1)
            db.session.add(new_option2)
            db.session.add(new_option3)
            db.session.add(new_option4)
            db.session.commit()
            return redirect(url_for('dashboard'))
    else:
        return render_template("create_question.html", username=session["username"], loggedin=True)

#delete question
@app.route("/delete_question/<int:id>", methods=["POST", "GET"])
def delete_question(id):
    if "username" in session:
        if request.method == 'POST':
            Answer.query.filter_by(question_id=id).delete()
            Option.query.filter_by(question_id=id).delete()
            question = Question.query.get(id)
            db.session.delete(question)
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            return render_template("delete_question.html", id=id, username=session["username"], loggedin=True)
    else:
        msg = ("Please enter a username and password")
        return render_template("index.html", error=msg)

#update question
@app.route("/update_question/<int:id>", methods=["POST", "GET"])
def update_question(id):
    if "username" in session:
        if request.method == 'POST':
            question_text = request.form["question_text"]
            Question.query.filter_by(id = id).update({'text': question_text})
            db.session.commit()
            option_text1 = request.form["option_text1"]
            option_text2 = request.form["option_text2"]
            option_text3 = request.form["option_text3"]
            option_text4 = request.form["option_text4"]
            Option.query.filter_by(question_id=id). filter_by(id=1).update({'text': option_text1})
            Option.query.filter_by(question_id=id).filter_by(id=2).update({'text': option_text2})
            Option.query.filter_by(question_id=id).filter_by(id=3).update({'text': option_text3})
            Option.query.filter_by(question_id=id).filter_by(id=4).update({'text': option_text4})
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            question = Question.query.get(id)
            option_text = [option.text for option in Option.query.filter_by(question_id=id)]
            return render_template("update_question.html", 
                                   question=question, username=session["username"], loggedin=True, option_text=option_text)
    else:
        msg = ("Please enter a username and password")
        return render_template("index.html", error=msg)

# Question Voting
@app.route("/votting/<int:id>", methods=["POST", "GET"])
def votting(id):
     if "username" in session:
            if request.method == 'POST':
                user_id = session["id"]
                question_id = request.form["question_id"]
                selected_option = request.form["option"]
                print(f"Voted on question {question_id} with option {selected_option}")
                existing_vote = db.session.query(db.session.query(Answer).filter(user_id==session['id'], question_id==question_id).exists()).scalar()
                if existing_vote:
                    msg = ("You have already voted for this question.")
                    questions = Question.query.all()
                    return render_template("questions.html", error=msg, loggedin=True, questions=questions, username=session["username"])
                else:
                    answer = Answer(user_id = user_id, question_id=question_id, option_id=selected_option, date_created=datetime.now(), date_updated = datetime.now() )
                    db.session.add(answer)
                    option = Option.query.filter_by(id=selected_option)[0]
                    Option.vote(option)
                    db.session.commit()
                    return redirect(url_for('dashboard'))
            else:
               question = get_question_by_id(id)
               option_text = get_option_text_by_question_id(id)  # Fetching the option texts
               option_id = get_option_ids_by_question_id(id)  # Fetching option IDs
               question = Question.query.get(id)
               option_list = Option.query.filter_by(question_id=id)
               option_text = [option.text for option in option_list]
               option_id = [option.id for option in option_list]
               return render_template("votting.html", question=question, username=session["username"], option_text=option_text, option_id =option_id, loggedin=True)
     else:
         msg = ("Please enter a username and password")
         return render_template("index.html", error=msg)

# Question Searching
@app.route("/search", methods=["GET", "POST"])
def search():
    if "username" in session:
        if request.method == "POST":
            search_term = request.form["search_term"]
            questions = db.session.query(Question).filter(Question.text.like(search_term)).all()
            return render_template("search.html", questions=questions, username=session["username"], loggedin=True, search_term=search_term)
        else:
            return render_template("search.html", username=session["username"], loggedin=True)
    else:
        msg = ("Please enter a username and password")
        return render_template("index.html", error=msg)

#view one question at a time
@app.route("/view_question/<int:id>")
def view_question(id):
    if "username" in session:
        question = get_question_by_id(id)
        question_text = Question.query.filter(Question.creator_id)
        option_text = get_option_text_by_question_id(id)
        option_id = get_option_ids_by_question_id(id)
        return render_template("view_question.html", question=question, username=session["username"], option_text=option_text, option_id=option_id, question_text = question_text, loggedin=True)
    else:
        msg = ("Please enter a username and password")
        return render_template("index.html", error=msg)

# view results
@app.route("/results/<int:id>")
def results(id):
    if "username" in session:
        question =get_question_by_id(id)
        options = db.session.query(Option).filter_by(question_id=id).all()
        total_votes = sum(option.vote_count for option in options)
        return render_template("results.html", question=question, results=results, username=session["username"], loggedin=True, options=options,total_votes=total_votes)
    else:
        msg = ("Please enter a username and password")
        return render_template("index.html", error=msg)

# update years
@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}

def get_question_by_id(question_id):
    question = db.session.query(Question).filter_by(id=question_id).first()
    return question

def get_option_text_by_question_id(id):
    option_text = db.session.query(Option).filter_by(question_id=id).all()
    return [option.text for option in option_text]

def get_option_ids_by_question_id(id):
    option_ids = db.session.query(Option).filter_by(question_id=id).all()
    return [option.id for option in option_ids]

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="localhost", port=int("5000"),debug=True)