import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
import re
app = Flask(__name__)

# Thiết lập thông tin kết nối đến cơ sở dữ liệu MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PassW0rk#123Wen",
    database="smart_locker"
)

# Bảng roles chứa thông tin về vai trò của người dùng
# Bảng users chứa thông tin về người dùng

def generate_user_id():
    cursor = db.cursor()
    cursor.execute("SELECT MAX(user_id) FROM users")
    result = cursor.fetchone()
    cursor.close()

    if result[0] is not None:
        current_id = int(result[0][1:])
        next_id = current_id + 1
        user_id = f"U{next_id:03d}"
    else:
        user_id = "U001"

    return user_id

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']  # Lấy giá trị của ô chọn quyền

        # Kiểm tra xác nhận mật khẩu
        if password != confirm_password:
            return "Mật khẩu và xác nhận mật khẩu không khớp"

        # Lấy role_id tương ứng với quyền được chọn
        cursor = db.cursor()
        cursor.execute("SELECT role_id FROM roles WHERE role_name = %s", (role,))
        role_id = cursor.fetchone()[0]

        # Tạo user_id mới
        user_id = generate_user_id()

        # Tiến hành lưu thông tin vào bảng users
        insert_query = "INSERT INTO users (user_id, name, mail, phone, role_id, password) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (user_id, name, email, phone, role_id, password)
        cursor.execute(insert_query, values)
        db.commit()
        cursor.close()

        return "Đăng ký thành công"

    return render_template('register.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run()
