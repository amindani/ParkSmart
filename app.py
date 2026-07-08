import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "parksmart2026"

# Fungsi get_db yang sudah diperbarui untuk Vercel + Supabase
def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL tidak ditemukan di Environment Variables!")
    
    url = urlparse(database_url)
    
    # Menggunakan sslmode='require' agar koneksi ke Supabase diizinkan
    conn = psycopg2.connect(
        dbname=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        sslmode='require',
        cursor_factory=RealDictCursor
    )
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
    rekomendasi = max(area, key=lambda x: x["kapasitas"] - x["terisi"]) if area else {"nama_area": "-"}
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
    cur.execute("SELECT COUNT(*) as count FROM riwayat")
    kendaraan = cur.fetchone()['count']
    cur.close()
    conn.close()
    return render_template("admin.html", area=area, total=total, terisi=terisi, kosong=total-terisi, kendaraan=kendaraan)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

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

# ... (Tambahkan rute tambah/edit/hapus/parkir lainnya di sini)

@app.errorhandler(404)
def notfound(e): return "<h2>404 Halaman Tidak Ditemukan</h2>", 404

if __name__ == "__main__":
    app.run(debug=True)
