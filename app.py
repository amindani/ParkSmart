from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "parksmart2026"

# Ganti dengan Connection String lengkap dari Supabase Anda
# Format: postgresql://[user]:[password]@[host]:[port]/[dbname]
DATABASE_URL = "postgresql://postgres:N%23J_r%26Az-485%2CZg@db.rcpbncqaensgcpnsipk.supabase.co:5432/postgres"

# ===========================================
# DATABASE (PostgreSQL)
# ===========================================

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

# ===========================================
# ROUTE LOGIN & DASHBOARD
# ===========================================

@app.route("/")
def home():
    if "role" not in session: return redirect("/login")
    if session["role"] == "admin": return redirect("/admin")
    return redirect("/dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        username = request.form["username"]
        password = request.form["password"]
        if role == "admin":
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s", (username, password))
            admin = cur.fetchone()
            cur.close()
            conn.close()
            if admin:
                session["role"]="admin"
                session["username"]=username
                return redirect("/admin")
            flash("Username / Password Salah")
            return redirect("/login")
        else:
            session["role"]="mahasiswa"
            session["username"]=username
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "role" not in session: return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM area_parkir")
    area = cur.fetchall()
    total = sum(a["kapasitas"] for a in area)
    terisi = sum(a["terisi"] for a in area)
    rekomendasi = max(area, key=lambda x: x["kapasitas"] - x["terisi"])
    cur.close()
    conn.close()
    return render_template("dashboard.html", area=area, total=total, terisi=terisi, kosong=total-terisi, rekomendasi=rekomendasi)

@app.route("/admin")
def admin():
    if session.get("role") != "admin": return redirect("/dashboard")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM area_parkir")
    area = cur.fetchall()
    total = sum(a["kapasitas"] for a in area)
    terisi = sum(a["terisi"] for a in area)
    cur.execute("SELECT COUNT(*) FROM riwayat")
    kendaraan = cur.fetchone()['count']
    cur.close()
    conn.close()
    return render_template("admin.html", area=area, total=total, terisi=terisi, kosong=total-terisi, kendaraan=kendaraan)

# ===========================================
# CRUD AREA PARKIR
# ===========================================

@app.route("/area")
def area():
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM area_parkir ORDER BY nama_area")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("area.html", area=data)

@app.route("/area/tambah", methods=["POST"])
def tambah_area():
    if session.get("role") != "admin": return redirect("/login")
    nama, kapasitas = request.form["nama_area"], int(request.form["kapasitas"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO area_parkir (nama_area, kapasitas, terisi) VALUES(%s, %s, %s)", (nama, kapasitas, 0))
    cur.close()
    conn.close()
    return redirect("/area")

@app.route("/area/edit/<int:id>", methods=["POST"])
def edit_area(id):
    if session.get("role") != "admin": return redirect("/login")
    nama, kapasitas = request.form["nama_area"], int(request.form["kapasitas"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE area_parkir SET nama_area=%s, kapasitas=%s WHERE id=%s", (nama, kapasitas, id))
    cur.close()
    conn.close()
    return redirect("/area")

@app.route("/area/hapus/<int:id>")
def hapus_area(id):
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM area_parkir WHERE id=%s", (id,))
    cur.close()
    conn.close()
    return redirect("/area")

# ===========================================
# PARKIR & RIWAYAT
# ===========================================

@app.route("/parkir/masuk", methods=["POST"])
def parkir_masuk():
    if "username" not in session: return redirect("/login")
    username, plat, jenis, area = session["username"], request.form["plat"], request.form["jenis"], request.form["area"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM area_parkir WHERE nama_area=%s", (area,))
    cek = cur.fetchone()
    if cek["terisi"] >= cek["kapasitas"]:
        cur.close()
        conn.close()
        flash("Area parkir penuh")
        return redirect("/dashboard")
    
    cur.execute("INSERT INTO riwayat (username, plat_nomor, jenis_kendaraan, area, jam_masuk, jam_keluar, status) VALUES(%s, %s, %s, %s, %s, %s, %s)",
                 (username, plat, jenis, area, datetime.now().strftime("%d-%m-%Y %H:%M"), "-", "Masuk"))
    cur.execute("UPDATE area_parkir SET terisi=terisi+1 WHERE nama_area=%s", (area,))
    cur.close()
    conn.close()
    return redirect("/dashboard")

@app.route("/parkir/keluar/<int:id>")
def parkir_keluar(id):
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM riwayat WHERE id=%s", (id,))
    data = cur.fetchone()
    if data:
        cur.execute("UPDATE riwayat SET jam_keluar=%s, status='Keluar' WHERE id=%s", (datetime.now().strftime("%d-%m-%Y %H:%M"), id))
        cur.execute("UPDATE area_parkir SET terisi=terisi-1 WHERE nama_area=%s AND terisi>0", (data["area"],))
    cur.close()
    conn.close()
    return redirect("/riwayat")

@app.route("/riwayat")
def riwayat():
    if "role" not in session: return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    if session["role"] == "admin": cur.execute("SELECT * FROM riwayat ORDER BY id DESC")
    else: cur.execute("SELECT * FROM riwayat WHERE username=%s ORDER BY id DESC", (session["username"],))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("riwayat.html", data=data)

# Tambahkan route error dan main di bawah sini
@app.errorhandler(404)
def notfound(e): return "<h2>404 Halaman Tidak Ditemukan</h2>", 404

if __name__ == "__main__":
    app.run(debug=True)