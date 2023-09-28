import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Thiết lập thông tin kết nối đến cơ sở dữ liệu MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PassW0rk#123Wen",
    database="smart_locker"
)
cursor = db.cursor()

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
def generate_history_id():
    cursor = db.cursor()
    cursor.execute("SELECT MAX(history_id) FROM histories")
    result = cursor.fetchone()
    cursor.close()

    if result[0] is not None:
        current_id = int(result[0][1:])
        next_id = current_id + 1
        history_id = f"H{next_id:03d}"
    else:
        history = "H001"

    return history_id

def generate_otp_id():
    cursor = db.cursor()
    cursor.execute("SELECT MAX(otp_id) FROM otps")
    result = cursor.fetchone()
    cursor.close()

    if result[0] is not None:
        current_id = int(result[0][1:])
        next_id = current_id + 1
        otp_id = f"{next_id:03d}"
    else:
        otp_id = "001"

    return otp_id
def send_email(mail, locker_id, otp_code):
    # Thiết lập thông tin SMTP
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "2051010118huyen@ou.edu.vn"
    smtp_password = "nguyenthithuhuyen"

    # Tạo email
    msg = MIMEMultipart()
    msg['From'] = "2051010118huyen@ou.edu.vn"
    msg['To'] = mail
    msg['Subject'] = "Thông tin đặt tủ"

    body = f"Tủ đã được cấp. Mã tủ: {locker_id},với mã OTP là: {otp_code} Vui lòng không cung cấp mã này cho bất kì ai.Mã OTP có thời gian sử dụng là 3 tiếng."
    msg.attach(MIMEText(body, 'plain'))

    # Gửi email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())

# Set lại status của locker_id
def reset_status():
    try:
        # Lấy danh sách các tủ có trạng thái "on" và end_time đã qua
        select_query = "SELECT locker_id, end_time FROM histories"
        cursor.execute(select_query)
        lockers_to_update = cursor.fetchall()

        current_time = datetime.now()

        # Kiểm tra và cập nhật trạng thái của các tủ
        for locker_id, end_time in lockers_to_update:
            if current_time > end_time:
                # Cập nhật trạng thái của tủ sang "off"
                update_locker_query = "UPDATE lockers SET status = 'off' WHERE locker_id = %s"
                cursor.execute(update_locker_query, (locker_id,))
                db.commit()
    except Exception as e:
        print(f"Lỗi: {e}")

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
    @app.route('/process_locker', methods=['GET','POST'])
def process_locker():
    try:
     if request.method == 'POST':
        name = request.form['name']
        mail = request.form['mail']
        phone = request.form['phone']
        start_time = request.form['start_time']


        # Kiểm tra xem số điện thoại có tồn tại trong bảng "users" hay không
        cursor.execute("SELECT user_id FROM users WHERE phone = %s", (phone,))
        user = cursor.fetchone()

        if user:
            # Kiểm tra xem có tủ nào có status "off" không
            cursor.execute("SELECT locker_id FROM lockers WHERE status = 'off'")
            available_lockers = cursor.fetchall()

            if available_lockers:
                # Random một tủ
                selected_locker = random.choice(available_lockers)[0]

                # Cập nhật status của tủ đã chọn
                cursor.execute("UPDATE lockers SET status = 'on' WHERE locker_id = %s", (selected_locker,))

                # Tạo mã OTP
                otp_code = random.randint(1000, 9999)

                # Tạo otp_id mới
                otp_id = generate_otp_id()
                cursor.execute("INSERT INTO otps (otp_id,otp_code, user_id, locker_id) VALUES (%s, %s, %s,%s)",
                               (otp_id, otp_code, user[0], selected_locker))
                db.commit()

                history_id = generate_history_id()
                # Tiến hành lưu thông tin vào bảng histories
                insert_query = "INSERT INTO histories (history_id,user_id, locker_id, start_time, end_time) VALUES (%s,%s, %s,%s,%s)"
                end_time = datetime.now() + timedelta(hours=3)  # Tính thời gian kết thúc sau 3 tiếng
                values = (history_id, user[0], selected_locker, start_time, end_time)
                cursor.execute(insert_query, values)
                db.commit()

                # Gửi email
                send_email(mail, selected_locker, otp_code)

                return jsonify("Đặt tủ thành công")

            else:
                return jsonify("Không có tủ trống.")

        else:
            return jsonify("Số điện thoại không tồn tại trong hệ thống.")

    except Exception as e:
        return f"Lỗi: {e}"
    return render_template('process_locker.html')

@app.route('/history')
def history():
    # Truy vấn lịch sử dùng tủ
            select_history_query = "SELECT history_id, user_id, locker_id, start_time, end_time FROM histories"
            cursor.execute(select_history_query)
            history_data = cursor.fetchall()

            # Đóng kết nối cơ sở dữ liệu
            # cursor.close()
            # db.close()
            return render_template('history.html', history_data=history_data)


if __name__ == '__main__':
    app.run()
