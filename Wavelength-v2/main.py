from flask import Flask,url_for, render_template, session, redirect, request
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase, ascii_lowercase
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

def generate_secret_key(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
            code += random.choice(ascii_lowercase)
        return code



app = Flask(__name__) # initialize application
app.config['SECRET_KEY'] =  generate_secret_key(10)
socketio = SocketIO(app)  # initialize the web socket using flask-socketIO

app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///users.db' #db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app) # initialize db-

# User model-
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True) #don't have to add value for user_id because it will automatically increase
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(100), nullable=True)
    clearance_level = db.Column(db.Integer, nullable=True)
    public_key = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Message(db.Model):
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    track_message_id = db.Column(db.Integer, db.ForeignKey('message.message_id'), nullable=False) #order messages came in
    message_content = db.Column(db.Text, nullable=False)


    def __repr__(self):
        return f'<Message {self.message_id}>'



rooms = {} # the number of rooms currently existing, begins empty

# method for generating random room codes
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code


# routes to html pages

@app.route('/')
def homepage():
    return render_template("home.html")

# this is the chat home page.
@app.route('/chatHome', methods=['GET', 'POST'])
def chat_room():  # put application's code here
    session.clear()  # clear all sessions
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)
        if not name:
            return render_template("chatHome.html", error="Please enter a name.", code=code, name=name)
        if join != False and not code:
            return render_template("chatHome.html", error="Please enter a code.", code=code, name=name)

        room = code
        if create is not False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("chatHome.html", error="Room does not exist.", code=code, name=name)

        #session stores data temporarily
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("chatHome.html")

# #this needs to be integrated to the soc_network page,
# def direct_message():
#     session.clear()  # clear all sessions
#     if request.method == "POST":
#         name = User.query.get("username")
#         create = request.form.get("create", False)
#         if create is not False:
#             rooms[room] = {"members": 0, "messages": []}
#
#         #session stores data temporarily
#         session["room"] = room
#         session["name"] = name
#         return redirect(url_for("room"))
#
#     return render_template("chatHome.html")
#

@app.route('/search')
def search():
    q = request.args.get('q')
    print(q)
    if q:
        results = User.query.filter(User.username.icontains(q)).limit(5).all()
    else:
        results = []
    return render_template("search_results.html", results=results)

@app.route('/soc_network', methods=['POST', 'GET'])
def soc_network():
    return render_template("soc_network.html")

#search bar for users in the databas
@app.route('/direct')

@app.route('/room')
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return render_template("home.html")
    return render_template("room.html", code=room)

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said {data['data']}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Find the user by username
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            # if login successful redirect to home page
            return redirect(url_for('homepage'))

        else:
            # Invalid user or pass
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Getting data from db
        username = request.form['username']
        full_name = request.form['full_name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        password = request.form['password']
        public_key = request.form['public_key']

        # Hash password before saving
        password_hash = generate_password_hash(password)

        # Check if the username or email already exists in db
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            # If user already exists display an error
            return render_template("register.html", error="Username or Email already exists.")

        # Create a new User object and new user to db
        new_user = User(
            username=username,
            full_name=full_name,
            phone_number=phone_number,
            email=email,
            password_hash=password_hash,
            public_key=public_key
        )

        # Add to the session and commit the transaction
        db.session.add(new_user)
        db.session.commit()
        # Redirect to a success or login page
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/references')
def references():

    return render_template("references.html")

@app.route('/source')
def source():
    return render_template("source.html")

@app.route('/contact')
def contact():

    return render_template("contact.html")

@app.route('/about')
def about():
    return render_template("about.html")
# socket functions


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room."}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room."}, to=room)
    print(f"{name} left the room {room}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
