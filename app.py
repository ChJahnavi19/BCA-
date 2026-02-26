import os
from werkzeug.utils import secure_filename

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

from models import db, User, JournalEntry, WishlistItem, Memory

# ================= APP SETUP =================
app = Flask(
    __name__,
    static_folder="images",
    static_url_path="/images"
)

app.secret_key = "travel_secret_key"

UPLOAD_FOLDER = "images"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ================= DATABASE =================
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ================= LOGIN ENFORCEMENT =================
@app.before_request
def enforce_login():
    allowed_routes = [
        "static",
        "root",
        "login",
        "signup",
        "logout",
        "game"   # allow game without blocking
    ]

    if request.endpoint in allowed_routes:
        return

    # Allow API routes
    if request.endpoint and request.endpoint.startswith("api_"):
        return

    if "user_id" not in session:
        return redirect(url_for("login"))

# ================= ROOT =================
@app.route("/")
def root():
    return redirect(url_for("login"))

# ================= AUTH =================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )

        db.session.add(user)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return render_template(
                "signup.html",
                error="Username or email already exists."
            )

        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(
            username=request.form["username"]
        ).first()

        if user and check_password_hash(
            user.password, request.form["password"]
        ):
            session["user_id"] = user.id
            return redirect(url_for("index"))

        return render_template(
            "login.html",
            error="Invalid credentials"
        )

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================= MAIN PAGE =================
@app.route("/index")
def index():
    memories = Memory.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template("index.html", memories=memories)

# ================= MEMORY =================
@app.route("/upload-memory", methods=["POST"])
def upload_memory():
    title = request.form.get("title")
    drive_link = request.form.get("drive_link")

    if not title or not drive_link:
        return "Invalid data", 400

    memory = Memory(
        title=title,
        drive_link=drive_link,
        user_id=session["user_id"]
    )

    db.session.add(memory)
    db.session.commit()

    return redirect(url_for("index"))

@app.route("/api/memories", methods=["GET"])
def get_memories():
    memories = Memory.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return jsonify([
        {
            "id": m.id,
            "title": m.title,
            "drive_link": m.drive_link
        } for m in memories
    ])

@app.route("/delete-memory/<int:memory_id>", methods=["POST"])
def delete_memory(memory_id):
    memory = Memory.query.filter_by(
        id=memory_id,
        user_id=session["user_id"]
    ).first()

    if memory:
        db.session.delete(memory)
        db.session.commit()

    return redirect(url_for("index"))

    if not memory:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(memory)
    db.session.commit()

    return jsonify({"message": "Deleted"})

# ================= JOURNAL =================
@app.route("/journal")
def journal():
    return render_template("journal.html")

@app.route("/api/journal", methods=["GET"])
def get_journal():
    entries = JournalEntry.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return jsonify([
        {
            "id": e.id,                 # ✅ REQUIRED FOR DELETE
            "location": e.location,
            "food": e.food,
            "memory": e.memory,
            "notes": e.notes
        } for e in entries
    ])

@app.route("/api/journal", methods=["POST"])
def save_journal():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400

    data = request.json

    entry = JournalEntry(
        location=data["location"],
        food=data.get("food"),
        memory=data.get("memory"),
        notes=data.get("notes"),
        user_id=session["user_id"]
    )

    db.session.add(entry)
    db.session.commit()

    return jsonify({"message": "Saved"})

@app.route("/api/journal/<int:entry_id>", methods=["DELETE"])
def delete_journal(entry_id):
    entry = JournalEntry.query.filter_by(
        id=entry_id,
        user_id=session["user_id"]
    ).first()

    if not entry:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(entry)
    db.session.commit()

    return jsonify({"message": "Deleted"})

# ================= WISHLIST =================
@app.route("/wishlist")
def wishlist():
    return render_template("wishlist.html")

@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    items = WishlistItem.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return jsonify([
        {
            "id": w.id,                 # ✅ REQUIRED FOR DELETE
            "place": w.place,
            "experience": w.experience,
            "notes": w.notes
        } for w in items
    ])

@app.route("/api/wishlist", methods=["POST"])
def save_wishlist():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400

    data = request.json

    item = WishlistItem(
        place=data["place"],
        experience=data.get("experience"),
        notes=data.get("notes"),
        user_id=session["user_id"]
    )

    db.session.add(item)
    db.session.commit()

    return jsonify({"message": "Saved"})

@app.route("/api/wishlist/<int:item_id>", methods=["DELETE"])
def delete_wishlist(item_id):
    item = WishlistItem.query.filter_by(
        id=item_id,
        user_id=session["user_id"]
    ).first()

    if not item:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Deleted"})

# ================= REGIONS =================
@app.route("/north")
def north():
    return render_template("North.html")

@app.route("/south")
def south():
    return render_template("South.html")

@app.route("/eastern")
def eastern():
    return render_template("Eastern.html")

@app.route("/western")
def western():
    return render_template("Western.html")

@app.route("/central")
def central():
    return render_template("Central.html")

@app.route("/northeast")
def northeast():
    return render_template("Northeast.html")

@app.route("/ut")
def ut():
    return render_template("UT.html")

@app.route("/pc")
def pc():
    return render_template("PC.html")

@app.route("/monuments")
def monuments():
    return render_template("Monuments.html")

# ================= OTHER =================
@app.route("/food")
def food():
    return render_template("food.html")

@app.route("/wildlife")
def wildlife():
    return render_template("wildlife.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")



@app.route("/game")
def game():
    words = [
        "tajmahal","kerala","rajasthan","varanasi","goa",
        "kashmir","andaman","ladakh","mysore","amritsar",
        "delhi","mumbai","kolkata","chennai","hyderabad",
        "bengaluru","sikkim","manali","ooty","udaipur",
        "jaipur","agra","konark","khajuraho","hampi",
        "shimla","darjeeling","rishikesh","meghalaya","pondicherry"
    ]
    return render_template("game.html", words=words)

@app.route("/gallery", methods=["GET", "POST"])
def gallery():
    if request.method == "POST":
        title = request.form.get("title")
        image = request.files.get("image")

        if image and title:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(image_path)

        return redirect(url_for("gallery"))

    # Get all images from folder
    image_files = os.listdir(app.config["UPLOAD_FOLDER"])

    return render_template("gallery.html", images=image_files)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")

        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template(
                "forgot_password.html",
                error="Email not found"
            )

        # Store user id temporarily in session
        session["reset_user_id"] = user.id

        return redirect(url_for("reset_password"))

    return render_template("forgot_password.html")

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if "reset_user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        new_password = request.form.get("password")

        if not new_password:
            return render_template(
                "reset_password.html",
                error="Password cannot be empty."
            )

        user = User.query.get(session["reset_user_id"])
        user.password = generate_password_hash(new_password)

        db.session.commit()
        session.pop("reset_user_id", None)

        return redirect(url_for("login"))

    return render_template("reset_password.html")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
