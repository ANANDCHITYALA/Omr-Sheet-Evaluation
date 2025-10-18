from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os, random, smtplib

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ============================
# DATABASE CONFIG
# ============================
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ============================
# MAIL CONFIG
# ============================
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "anandchityalach@gmail.com"  # your Gmail
app.config["MAIL_PASSWORD"] = "zfgjfydipuhafqfu"           # Gmail App Password

db = SQLAlchemy(app)
mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

# ============================
# MODELS
# ============================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    roll = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True)
    contact = db.Column(db.String(20))
    course = db.Column(db.String(100))
    batch = db.Column(db.String(50))
    exam_set = db.Column(db.String(10))
    password = db.Column(db.String(120))
    role = db.Column(db.String(20))  # student / lecturer / admin
    is_approved = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# ============================
# ROUTES - BASIC PAGES
# ============================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/student")
def student():
    return render_template("student.html")

@app.route("/lecturer")
def lecturer():
    return render_template("lecturer.html")

@app.route("/result")
def result():
    return render_template("result.html")

@app.route("/admin_portal")
def admin_portal():
    return render_template("admin_login.html")

@app.route("/admin")
def admin():
    return render_template("admin_dashboard.html")




# ============================
# STUDENT REGISTRATION
# ============================
@app.route("/register_student", methods=["POST"])
def register_student():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    required_fields = ["name", "email", "password"]
    if not all(data.get(field) for field in required_fields):
        return jsonify({"error": "All required fields must be filled"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "User already exists"}), 400

    new_user = User(
        name=data.get("name"),
        email=data.get("email"),
        password=data.get("password"),
        role="student",
        is_approved=False
    )
    db.session.add(new_user)
    db.session.commit()

    # Notify admin
    try:
        msg = Message(
            "New Student Registration Request",
            sender=app.config["MAIL_USERNAME"],
            recipients=["anandchityalach@gmail.com"]
        )
        msg.body = f"""
New Student Registration Request:

Name: {new_user.name}
Email: {new_user.email}

Please review and approve in the Admin Dashboard.
"""
        mail.send(msg)
    except Exception as e:
        print(f"[WARN] Could not send admin mail: {e}")

    return jsonify({"message": "✅ Registration submitted successfully. Awaiting admin approval."}), 200

# ============================
# STUDENT LOGIN
# ============================
@app.route("/student_login", methods=["POST"])
def student_login():
    data = request.get_json() or request.form
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email, role="student").first()
    if not user:
        return jsonify({"error": "No account found"}), 404
    if not user.is_approved:
        return jsonify({"error": "Your account is pending admin approval"}), 403
    if user.password != password:
        return jsonify({"error": "Invalid password"}), 400

    session["student_email"] = email
    return jsonify({"message": "🎉 Login successful!", "redirect": url_for("upload_omr")}), 200

# ============================
# LECTURER REGISTRATION
# ============================
@app.route("/register_lecturer", methods=["POST"])
def register_lecturer():
    data = request.form
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "User already exists"}), 400

    new_user = User(
        name=data["name"],
        email=data["email"],
        password=data["password"],
        role="lecturer",
        is_approved=False
    )
    db.session.add(new_user)
    db.session.commit()

    msg = Message(
        "New Lecturer Registration Request",
        sender=app.config["MAIL_USERNAME"],
        recipients=["anandchityalach@gmail.com"]
    )
    msg.body = f"New lecturer '{data['name']}' has registered. Please review and approve."
    mail.send(msg)

    return jsonify({"message": "Lecturer registration submitted for approval."}), 200

# ============================
# ADMIN LOGIN + OTP
# ============================
ALLOWED_ADMINS = ["anandchityalach@gmail.com"]

@app.route("/admin_login", methods=["POST"])
def admin_login():
    data = request.json
    if data["email"] not in ALLOWED_ADMINS:
        return jsonify({"error": "Unauthorized"}), 403

    otp = str(random.randint(100000, 999999))
    session["admin_otp"] = otp
    session["pending_admin"] = data["email"]

    try:
        msg = Message(
            subject="Innomatics Admin OTP",
            sender=app.config["MAIL_USERNAME"],
            recipients=[data["email"]],
            body=f"Your OTP is {otp}"
        )
        mail.send(msg)
    except (smtplib.SMTPException, Exception) as e:
        print(f"[ERROR] Could not send mail: {e}")
        return jsonify({"message": f"⚠️ Email failed. OTP: {otp}"}), 200

    return jsonify({"message": "✅ OTP sent to admin email."})

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json
    if data["otp"] == session.get("admin_otp"):
        session["verified_admin"] = session["pending_admin"]
        session.pop("admin_otp", None)
        session.pop("pending_admin", None)
        return jsonify({"message": "✅ OTP verified"}), 200
    return jsonify({"error": "❌ Invalid OTP"}), 400

# ============================
# ADMIN ACTIONS
# ============================
# @app.route("/get_users")
# def get_users():
#     users = User.query.all()
#     return jsonify([
#         {"name": u.name, "email": u.email, "role": u.role, "is_approved": u.is_approved}
#         for u in users
#     ])

@app.route("/get_users")
def get_users():
    if "verified_admin" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    users = User.query.all()
    return jsonify([
        {"name": u.name, "email": u.email, "role": u.role, "is_approved": u.is_approved}
        for u in users
    ])

# APPROVE USER — send password setup mail
@app.route("/approve_user", methods=["POST"])
def approve_user():
    if "verified_admin" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_approved = True
    db.session.commit()

    token = s.dumps(user.email, salt="password-setup")
    reset_link = url_for("set_password", token=token, _external=True)

    try:
        msg = Message(
            subject="🎉 Approved! Set Your Password - Innomatics Portal",
            sender=app.config["MAIL_USERNAME"],
            recipients=[user.email],
            body=f"""
Hello {user.name},

Your registration has been approved ✅

Please click the link below to set your password:
{reset_link}

This link expires in 1 hour.

Best Regards,
Innomatics Research Labs
"""
        )
        mail.send(msg)
    except Exception as e:
        print(f"[ERROR] Could not send approval mail: {e}")

    return jsonify({"message": f"{user.name} approved ✅ and email sent."})

@app.route("/reject_user", methods=["POST"])
def reject_user():
    if "verified_admin" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"{user.name} rejected ❌"})
    return jsonify({"error": "User not found"})

# ============================
# SET PASSWORD (From Email)
# ============================
@app.route("/set_password/<token>", methods=["GET", "POST"])
def set_password(token):
    try:
        email = s.loads(token, salt="password-setup", max_age=3600)
    except Exception:
        return "❌ Invalid or expired link.", 400

    if request.method == "POST":
        new_password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if not user:
            return "User not found.", 404
        user.password = new_password
        db.session.commit()
        return render_template("password_success.html", name=user.name)

    return render_template("set_password.html", email=email)

# ============================
# OMR UPLOAD PAGE
# ============================
@app.route("/upload_omr", methods=["GET", "POST"])
def upload_omr():
    if "student_email" not in session:
        return redirect(url_for("student"))
    if request.method == "POST":
        file = request.files["omr_file"]
        if file:
            upload_folder = "uploads"
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, file.filename)
            file.save(filepath)
            return "✅ OMR Uploaded Successfully!"
    return render_template("upload_omr.html")

# ============================
# LOGOUT
# ============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ============================
# RUN
# ============================
if __name__ == "__main__":
    app.run(debug=True, port=8080)
