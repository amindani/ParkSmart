from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "parksmart2026"

DATABASE = "database.db"

# ===========================================
# DATABASE
# ===========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS admin(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS area_parkir(id INTEGER PRIMARY KEY AUTOINCREMENT, nama_area TEXT, kapasitas INTEGER, terisi INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS riwayat(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, plat_nomor TEXT, jenis_kendaraan TEXT, area TEXT, jam_masuk TEXT, jam_keluar TEXT, status TEXT)")
    conn.commit()

    admin = cur.execute("SELECT * FROM admin").fetchone()
    if admin is None:
        cur.execute("INSERT INTO admin(username,password) VALUES('admin','admin123')")
    
    area = cur.execute("SELECT * FROM area_parkir").fetchone()
    if area is None:
        cur.execute("INSERT INTO area_parkir(nama_area,kapasitas,terisi) VALUES ('A',50,20), ('B',40,35), ('C',60,15)")
    conn.commit()
    conn.close()

init_db()

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
            admin = conn.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password)).fetchone()
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
    area = conn.execute("SELECT * FROM area_parkir").fetchall()
    total = sum(a["kapasitas"] for a in area)
    terisi = sum(a["terisi"] for a in area)
    rekomendasi = max(area, key=lambda x: x["kapasitas"] - x["terisi"])
    conn.close()
    return render_template("dashboard.html", area=area, total=total, terisi=terisi, kosong=total-terisi, rekomendasi=rekomendasi)

@app.route("/admin")
def admin():
    if session.get("role") != "admin": return redirect("/dashboard")
    conn = get_db()
    area = conn.execute("SELECT * FROM area_parkir").fetchall()
    total = sum(a["kapasitas"] for a in area)
    terisi = sum(a["terisi"] for a in area)
    kendaraan = conn.execute("SELECT COUNT(*) FROM riwayat").fetchone()[0]
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
    data = conn.execute("SELECT * FROM area_parkir ORDER BY nama_area").fetchall()
    conn.close()
    return render_template("area.html", area=data)

@app.route("/area/tambah", methods=["POST"])
def tambah_area():
    if session.get("role") != "admin": return redirect("/login")
    nama, kapasitas = request.form["nama_area"], int(request.form["kapasitas"])
    conn = get_db()
    conn.execute("INSERT INTO area_parkir (nama_area, kapasitas, terisi) VALUES(?,?,?)", (nama, kapasitas, 0))
    conn.commit()
    conn.close()
    flash("Area berhasil ditambahkan")
    return redirect("/area")

@app.route("/area/edit/<int:id>", methods=["POST"])
def edit_area(id):
    if session.get("role") != "admin": return redirect("/login")
    nama, kapasitas = request.form["nama_area"], int(request.form["kapasitas"])
    conn = get_db()
    conn.execute("UPDATE area_parkir SET nama_area=?, kapasitas=? WHERE id=?", (nama, kapasitas, id))
    conn.commit()
    conn.close()
    flash("Area berhasil diubah")
    return redirect("/area")

@app.route("/area/hapus/<int:id>")
def hapus_area(id):
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    conn.execute("DELETE FROM area_parkir WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/area")

# ===========================================
# PARKIR, RIWAYAT & LAINNYA
# ===========================================

@app.route("/parkir/masuk", methods=["POST"])
def parkir_masuk():
    if "username" not in session: return redirect("/login")
    username, plat, jenis, area = session["username"], request.form["plat"], request.form["jenis"], request.form["area"]
    conn = get_db()
    cek = conn.execute("SELECT * FROM area_parkir WHERE nama_area=?", (area,)).fetchone()
    if cek["terisi"] >= cek["kapasitas"]:
        conn.close()
        flash("Area parkir penuh")
        return redirect("/dashboard")
    conn.execute("INSERT INTO riwayat (username, plat_nomor, jenis_kendaraan, area, jam_masuk, jam_keluar, status) VALUES(?,?,?,?,?,?,?)",
                 (username, plat, jenis, area, datetime.now().strftime("%d-%m-%Y %H:%M"), "-", "Masuk"))
    conn.execute("UPDATE area_parkir SET terisi=terisi+1 WHERE nama_area=?", (area,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/parkir/keluar/<int:id>")
def parkir_keluar(id):
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    data = conn.execute("SELECT * FROM riwayat WHERE id=?", (id,)).fetchone()
    if data:
        conn.execute("UPDATE riwayat SET jam_keluar=?, status='Keluar' WHERE id=?", (datetime.now().strftime("%d-%m-%Y %H:%M"), id))
        conn.execute("UPDATE area_parkir SET terisi=terisi-1 WHERE nama_area=? AND terisi>0", (data["area"],))
    conn.commit()
    conn.close()
    return redirect("/riwayat")

@app.route("/riwayat")
def riwayat():
    if "role" not in session: return redirect("/login")
    conn = get_db()
    if session["role"] == "admin": data = conn.execute("SELECT * FROM riwayat ORDER BY id DESC").fetchall()
    else: data = conn.execute("SELECT * FROM riwayat WHERE username=? ORDER BY id DESC", (session["username"],)).fetchall()
    conn.close()
    return render_template("riwayat.html", data=data)

@app.route("/laporan")
def laporan():
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM riwayat").fetchone()[0]
    motor = conn.execute("SELECT COUNT(*) FROM riwayat WHERE jenis_kendaraan='Motor'").fetchone()[0]
    mobil = conn.execute("SELECT COUNT(*) FROM riwayat WHERE jenis_kendaraan='Mobil'").fetchone()[0]
    area = conn.execute("SELECT nama_area, kapasitas, terisi FROM area_parkir ORDER BY nama_area").fetchall()
    conn.close()
    return render_template("laporan.html", total=total, motor=motor, mobil=mobil, area=area)

@app.route("/riwayat/hapus/<int:id>")
def hapus_riwayat(id):
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    conn.execute("DELETE FROM riwayat WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/riwayat")

@app.route("/cari")
def cari():
    if "role" not in session: return redirect("/login")
    keyword = request.args.get("keyword", "")
    conn = get_db()
    if session["role"] == "admin":
        data = conn.execute("SELECT * FROM riwayat WHERE plat_nomor LIKE ? OR username LIKE ? ORDER BY id DESC", (f"%{keyword}%", f"%{keyword}%")).fetchall()
    else:
        data = conn.execute("SELECT * FROM riwayat WHERE username=? AND plat_nomor LIKE ? ORDER BY id DESC", (session["username"], f"%{keyword}%")).fetchall()
    conn.close()
    return render_template("riwayat.html", data=data)

@app.route("/reset")
def reset():
    if session.get("role") != "admin": return redirect("/login")
    conn = get_db()
    conn.execute("DELETE FROM riwayat")
    conn.execute("UPDATE area_parkir SET terisi=0")
    conn.commit()
    conn.close()
    flash("Data berhasil direset")
    return redirect("/admin")

@app.route("/api/parkir")
def api():
    conn = get_db()
    area = conn.execute("SELECT * FROM area_parkir ORDER BY nama_area").fetchall()
    conn.close()
    hasil = [{"nama_area": a["nama_area"], "terisi": a["terisi"], "kapasitas": a["kapasitas"]} for a in area]
    return {"status": "success", "data": hasil}

@app.errorhandler(404)
def notfound(e): return "<h2>404 Halaman Tidak Ditemukan</h2>", 404

# Posisikan ini WAJIB di paling bawah
if __name__ == "__main__":
    app.run(debug=True)