import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Thiết lập thông tin kết nối đến cơ sở dữ liệu MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PassW0rk#123Wen",
    database="smart_locker"
)


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
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        # Kiểm tra xác nhận mật khẩu
        if password != confirm_password:
            return "Mật khẩu và xác nhận mật khẩu không khớp"

        # Lấy role_id tương ứng với quyền được chọn
        cursor = db.cursor()
        cursor.execute("SELECT role_id FROM roles WHERE role_name = %s", (role,))
        role_id = cursor.fetchone()[0]

        # Kiểm tra xem số điện thoại đã tồn tại hay chưa
        cursor.execute("SELECT phone FROM users WHERE phone = %s", (phone,))
        existing_user = cursor.fetchone()
        if existing_user:
            return "Số điện thoại đã tồn tại. Vui lòng nhập số điện thoại khác."

        # Tạo user_id mới
        user_id = generate_user_id()

        # Tiến hành lưu thông tin vào bảng users
        insert_query = "INSERT INTO users (user_id, name, mail, phone, role_id, password) VALUES (%s, %s, %s, %s, %s, %s)"
        values = (user_id, name, email, phone, role_id, password)
        cursor.execute(insert_query, values)

        db.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT user_id, name FROM users WHERE phone = %s AND password = %s", (phone, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            user_name = user[1]
            cursor.close()

            return render_template('user.html', user_name=user_name)  # Truyền tên người dùng vào template

        else:
            error_message = "Sai số điện thoại hoặc mật khẩu. Vui lòng thử lại."

            cursor.close()

            return render_template('login.html', error_message=error_message)

    return render_template('login.html')


@app.route('/user')
def user():

    if 'user_id' in session:
        return render_template('user.html')
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
