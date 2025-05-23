import flask
from flask import Flask, url_for, render_template, session, redirect, request, flash, jsonify
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import random
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from string import ascii_uppercase, ascii_lowercase
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from randimage import get_random_image
import matplotlib.pyplot as profile_picture
import shutil
import os
from datetime import datetime
import json


def generate_secret_key(length): #generate secret key
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
            code += random.choice(ascii_lowercase)
        return code


app = Flask(__name__)  # initialize application
app.config['SECRET_KEY'] = generate_secret_key(10)
socketio = SocketIO(app)  # initialize the web socket using flask-socketIO
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  #db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)  # initialize db-

class Mailbox(db.Model):
    mailbox_id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    payload = db.Column(db.Text, nullable=False)  # base64 encoded symmetric key for now
    type = db.Column(db.String(50), nullable=False, default="symmetric_key")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# User model-
class User(UserMixin, db.Model): # UserMixin needed for login functionality
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(100), nullable=True)
    clearance_level = db.Column(db.Integer, nullable=True)
    profile_pic = db.Column(db.String(120), nullable=True)
    public_key = db.Column(db.String(512), nullable=True)



    def get_id(self):
        return self.user_id

    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def __repr__(self):
        return f'<User {self.username}>'

class Message(db.Model):
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    message_content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Message {self.message_id}>'

class DirectRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    room_code = db.Column(db.String(20), unique=True, nullable=False)


    def __repr__(self):
        return f'<DirectRoom {self.room_code}>'


rooms = {}  # the number of rooms currently existing, begins empty
directRooms = {}

# login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    #loads the logged-in user

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
    just_logged_in = session.pop('just_logged_in', False)
    return render_template("home.html",just_logged_in=just_logged_in, currentUser = current_user)

# this is the chat home page.
@app.route('/chatHome', methods=['GET', 'POST'])
@login_required
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

@app.route('/create_direct_room', methods=["POST"])
@login_required
def create_direct_room():

    recipient_username = request.form.get("username")
    recipient = User.query.filter_by(username=recipient_username).first()

    if recipient:
        user1, user2 = sorted([current_user.user_id, recipient.user_id]) #username
        room_code = f"{user1}{user2}"  # or use your existing logic

        room = DirectRoom.query.filter_by(user1=user1, user2=user2).first()
        if not room:
            room = DirectRoom(user1=user1, user2=user2, room_code=room_code)
            db.session.add(room)
            db.session.commit()

            directRooms[room] = {"members": 0, "messages": []}

        return jsonify(room_code=room.room_code)
    else:
        return jsonify(error="User not found"), 404



@app.route('/directRoom/<room_code>')
@login_required
def direct_chat_room(room_code):
    room = DirectRoom.query.filter_by(room_code=room_code).first()
    if not room:
        return "Room not found", 404

    if current_user.user_id == room.user1_id:
        recipient = User.query.filter_by(user_id=room.user2_id).first()
    else:
        recipient = User.query.filter_by(user_id=room.user1_id).first()

    just_created_room = session.pop("just_created_room", False)

    return render_template("directRoom.html", room=room_code, recipient=recipient, currentUser=current_user, just_created_room=just_created_room)

@app.route('/get_or_create_direct_room/<target_username>')
def get_or_create_direct_room(target_username):
    target_user = User.query.filter_by(username=target_username).first()
    user_now = User.query.filter_by(username=current_user.username).first()
    if not target_user:
        return jsonify(success=False, message="target User not found.")

    user1_id, user2_id = sorted([user_now.user_id, target_user.user_id])
    room_code = f"{user1_id}_{user2_id}"

    existing_room = DirectRoom.query.filter_by(room_code=room_code).first()
    print("The Room Exists: ", existing_room)

    if existing_room:
        print("Returning True")
        return jsonify(success=True, room_code=existing_room.room_code)
    else:
        try:
            new_room = DirectRoom(user1_id=user1_id, user2_id=user2_id, room_code=room_code)
            db.session.add(new_room)
            db.session.commit()
            session['just_created_room'] = True
            return jsonify(success=True, room_code=new_room.room_code)
        except Exception as e:
            print(f"Exception creating direct room: {e}")
            db.session.rollback()
            return jsonify(success=False, message="Failed to create chat room.")

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    q = request.args.get('q') or request.args.get('q')
    print(q)
    if q:
        results = User.query.filter(User.username.icontains(q)).limit(5).all()
        print(results)
    else:
        results = []
    return render_template("search_results.html", results=results)

@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html")


@app.route('/soc_network', methods=['POST', 'GET'])
@login_required
def soc_network():
    return render_template("soc_network.html")


@app.route('/room')
@login_required
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return render_template("home.html")
    return render_template("room.html", code=room)


@socketio.on("message")
@login_required
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    # rooms[room]["messages"].append(content)

    print(f"{session.get('name')} said {data['data']}")

@socketio.on("join")
def handle_join(data):
    user_id = data['user_id']
    join_room(str(user_id))

@socketio.on("send_message")
def handle_direct_message(data):
    recipient_id = data["recipient_id"]
    content = data["content"]

    new_message = Message(
        sender_id = current_user.user_id,
        recipient_id = recipient_id,
        message_content = content,
        timestamp = datetime.now(),
    )
    db.session.add(new_message)
    db.session.commit()

    recipient_name = User.query.filter_by(user_id=recipient_id).first().username

    try:
        nonce_b64, ciphertext_b64 = content.split(":")
        print(nonce_b64 + "\n" + ciphertext_b64)
        message_data = {
            'id': new_message.message_id,
            'sender_id': str(current_user.user_id),
            'recipient_name': recipient_name,
            'content': ciphertext_b64,
            'nonce': nonce_b64,
            'timestamp': new_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

        emit("receive_message", message_data, room=str(current_user.user_id))
        emit("receive_message", message_data, room=str(recipient_id))
    except Exception as e:
        print(e)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Find the user by username
        user = User.query.filter_by(username=username).first()
        #print(user)
        if user and check_password_hash(user.password_hash, password) is True:
            # if login successful redirect to home page
            login_user(user, remember=True)  #log in the user
            print(user.username, "logged in successfully")

            session['just_logged_in'] = True

            return redirect(url_for('homepage'))

        else:
            # Invalid user or pass
            return redirect(url_for("login"))  #, error="Invalid username or password")

    return render_template("login.html")


@app.route('/logout')
@login_required
def logout():
    logout_user() # immediately logs out user
    return flask.redirect(flask.url_for('homepage')) # takes them to the homepage, the user is defaulted as guest, and not logged in


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Getting data from db
        user_id = request.form.get('user_id')
        username = request.form['username']
        full_name = request.form['full_name']
        phone_number = request.form['phone_number']
        email = request.form['email']
        password = request.form['password']
        public_key = request.form['public_key']
        # Hash password before saving
        password_hash = generate_password_hash(password)

        # generate profile picture
        pfp_size = (128, 128)  # size of pfp
        pfp = get_random_image(pfp_size)  # makes pfp
        profile_picture.imsave(f"{username}.png", pfp)  # save pfp as an image
        current_dir = os.getcwd()
        target_dir = "static/profile_pics"
        rel = os.path.join(current_dir, target_dir)
        pfp_path = shutil.move(f"{username}.png", rel)  # save pfp path for User object
        # Check if the username or email already exists in db
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            # If user already exists display an error
            return render_template("register.html", error="Username or Email already exists.")
        else:
        # Create a new User object and new user to db
            try:
                new_user = User(
                    user_id=user_id,
                    username=username,
                    full_name=full_name,
                    phone_number=phone_number,
                    email=email,
                    password_hash=password_hash,
                    profile_pic=pfp_path,
                    public_key=public_key
                )
                # Add to the session and commit the transaction
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user, remember=True)
                # Redirect to a success or login page
                return redirect(url_for('homepage'))
            except Exception as e:
                print(e)
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

@app.route('/change_info', methods=['GET', 'POST'])
@login_required
def change_info():
    user = current_user
    current_dir = os.getcwd()
    current_username = session.get("username")
    current_phone = session.get("phone_number")
    current_email = session.get("email")
    new_username = request.form.get("new_username")
    new_email = request.form.get("new_email")
    new_phone = request.form.get("new_phone")
    #logged-in user changing user information
    if request.method == 'POST':
        if new_username != current_username and not "":
            old_path = os.path.join(current_dir, f"{user.username}.png")
            new_path = os.path.join(current_dir, f"{new_username}.png")
            os.rename(old_path, new_path)
            user.username = new_username
        elif new_username == current_username or new_username == "" :
            pass
        if new_phone != current_phone and not "":

            user.phone_number = new_phone
        elif new_phone == current_phone or new_phone == "":
            pass
        if new_email != current_email and not "":
            old_path = os.path.join(current_dir, f"{user.username}.png")
            new_path = os.path.join(current_dir, f"{new_username}.png")
            os.rename(old_path, new_path)
            user.email = new_email
        elif new_email == current_email or new_email== "":
            pass
        db.session.commit()

    return render_template("change_info.html")

@app.route('/api/send_symmetric_key', methods=['POST'])
@login_required
def send_symmetric_key():
    data = request.get_json()
    recipient_id = data["recipient_id"]
    payload = data["symmetric_key"]

    mailbox_entry = Mailbox(
        recipient_id=recipient_id,
        sender_id=current_user.user_id,
        payload=json.dumps(payload),
        type="symmetric_key"
    )
    db.session.add(mailbox_entry)
    db.session.commit()

    return jsonify({'message': 'Symmetric key sent to mailbox.'}), 200

@app.route('/api/get_mailbox', methods=['GET'])
@login_required
def get_mailbox():
    if not current_user.is_authenticated:
        # print("not authenticated")
        return jsonify([])
    else:
        # print("authenticated")
        entries = Mailbox.query.filter_by(recipient_id=current_user.user_id).all()

        mailbox_data = [{
            'id': entry.mailbox_id,
            'sender_id': entry.sender_id,
            'payload': json.loads(entry.payload),
            'type': entry.type,
            'created_at': entry.created_at.isoformat()
        } for entry in entries]

        for entry in entries:
            db.session.delete(entry)
        db.session.commit()
        # if len(mailbox_data) != 0:
        #     print(type(mailbox_data[0]['payload']))
        return jsonify(mailbox_data)

@app.route('/api/message_history/<int:recipient_id>', methods=['GET'])
@login_required
def message_history(recipient_id):
    messages = (
        Message.query.filter(
            ((Message.sender_id == current_user.user_id) & (Message.recipient_id == recipient_id)) |
            ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user.user_id))
        ).order_by(Message.timestamp.asc()).all()
    )

    message_data = [{
        "sender": str(msg.sender_id),
        "recipient": str(recipient_id),
        "message": msg.message_content,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    } for msg in messages]

    return jsonify(message_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
