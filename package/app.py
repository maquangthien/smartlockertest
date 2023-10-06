import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import string

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'


db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="PassW0rk#123Wen",
    database="smart_locker1"
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
        cursor.execute("SELECT user_id, name, role_id FROM users WHERE phone = %s AND password = %s", (phone, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            user_name = user[1]
            role_id = user[2]

            cursor.close()

            if role_id == '3':
                return render_template('otp_delivery.html', user_name=user_name)
            elif role_id == '2':
                return render_template('process_locker.html', user_name=user_name)
            elif role_id == '1':
                return render_template('admin.html', user_name=user_name)
            else:
                error_message = "Vai trò không hợp lệ."
                return render_template('login.html', error_message=error_message)

        else:
            error_message = "Sai số điện thoại hoặc mật khẩu. Vui lòng thử lại."
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


@app.route('/process_locker', methods=['POST'])
def process_locker():
    cursor = db.cursor()

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
                cursor.execute("SELECT locker_id FROM lockers WHERE status = 'off' LIMIT 1")
                available_locker = cursor.fetchone()

                if available_locker:
                    locker_id = available_locker[0]

                    # Sinh mã OTP cho từng người liên quan
                    otp_sender = generate_otp()
                    otp_deliver = generate_otp()
                    otp_receiver = generate_otp()
                    expiration_time = datetime.now() + timedelta(hours=3)

                    # Tạo mã codeorders và lưu vào biến
                    codeorders = generate_random_code()

                    # Lưu các mã OTP vào bảng "otps"
                    cursor.execute(
                        "INSERT INTO otps (otp_sender, otp_deliver, otp_receiver, expiration_time, codeorders) VALUES (%s, %s, %s, %s, %s)",
                        (otp_sender, otp_deliver, otp_receiver, expiration_time, codeorders))
                    db.commit()
                    user_sender = user[0]  # Đây là user_id của người gửi, bạn cần lấy từ user đã đăng nhập
                    start_time = datetime.now()

                    # Sử dụng cùng biến codeorders trong truy vấn SQL và khi gán giá trị vào bảng "histories"
                    cursor.execute(
                        "INSERT INTO histories (codeorders, user_sender, start_time) VALUES (%s, %s, %s)",
                        (codeorders, user_sender, start_time))
                    db.commit()

                    # Lưu thông tin mã OTP và codeorders vào biến session
                    session['otp_sender'] = otp_sender
                    session['otp_deliver'] = otp_deliver
                    session['otp_receiver'] = otp_receiver
                    session['codeorders'] = codeorders  # Lưu codeorders vào session

                    cursor.close()

                    if send_otp_sender(mail, otp_sender):
                        # Chuyển hướng người gửi đến trang otp_sender.html
                        return redirect(url_for('otp_sender'))
                else:
                    return "Không có tủ trống để đặt."
            else:
                return "Số điện thoại không tồn tại trong hệ thống."
    except Exception as e:
        # Xử lý lỗi ở đây nếu có
        return str(e)
    return render_template('process_locker.html')


def generate_random_code():
    digits = ''.join(random.choices(string.digits, k=4))
    letters = ''.join(random.choices(string.ascii_letters, k=4))
    code = digits + letters
    return code

def generate_otp():
    # Sinh mã OTP ngẫu nhiên, ví dụ mã OTP gồm 4 chữ số
    return str(random.randint(1000, 9999))

def send_otp_sender(mail, otp_sender):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "2051010118huyen@ou.edu.vn"
    smtp_password = "nguyenthithuhuyen"

    # Tạo email
    msg = MIMEMultipart()
    msg['From'] = "2051010118huyen@ou.edu.vn"
    msg['To'] = mail
    msg['Subject'] = "Thông tin đặt tủ"

    body = f"Mã OTP là: {otp_sender}\nVui lòng không cung cấp mã này cho bất kì ai. Mã OTP có thời gian sử dụng là 3 tiếng."
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Gửi email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, mail, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Lỗi khi gửi email: {str(e)}")
        return False
@app.route('/otp_sender')
def otp_sender():
    # Kiểm tra xem có mã OTP trong biến session không
    if 'otp_sender' in session:
        otp_sender = session['otp_sender']
        return render_template('otp_sender.html', otp_sender=otp_sender)
    else:
        return redirect(url_for('process_locker'))

@app.route('/unlock_locker', methods=['POST'])
def unlock_locker():
    if request.method == 'POST':
        otp_sender = request.form['otp_sender']
        codeorders = session.get('codeorders')  # Lấy giá trị codeorders từ session

        # Kiểm tra xác thực OTP
        if otp_sender == session.get('otp_sender'):
            cursor = db.cursor()

            # Tìm tủ trống (status='off')
            cursor.execute("SELECT locker_id FROM lockers WHERE status = 'off' LIMIT 1")
            available_locker = cursor.fetchone()

            if available_locker:
                locker_id = available_locker[0]

                # Cập nhật trạng thái tủ thành "on" (status='on')
                cursor.execute("UPDATE lockers SET status = 'on' WHERE locker_id = %s", (locker_id,))
                db.commit()

                # Tạo mã ngẫu nhiên
                otp_processing = generate_otp()
                code_orders = generate_random_code()

                # Truy vấn thông tin từ bảng histories dựa trên codeorders
                cursor.execute("SELECT user_sender, start_time FROM histories WHERE codeorders = %s", (codeorders,))
                history_info = cursor.fetchone()

                if history_info:
                    user_sender = history_info[0]
                    start_time = history_info[1]

                    # Tiến hành cập nhật thông tin vào bảng otpprocessing
                    cursor.execute(
                        "INSERT INTO otpprocessing (user_id, locker_id, otp, codeorders) VALUES (%s, %s, %s, %s)",
                        (user_sender, locker_id, otp_sender, codeorders)
                    )
                    db.commit()
                else:
                    # Xử lý trường hợp không tìm thấy thông tin trong bảng histories
                    return "Không tìm thấy thông tin từ bảng histories."

                db.commit()

                cursor.close()

                # Xóa mã OTP sau khi sử dụng
                session.pop('otp_sender', None)

                # Chuyển hướng đến trang thông báo và hiển thị tủ đã mở
                return render_template('unlock_success.html', locker_number=locker_id)

    # Nếu xác thực không thành công hoặc không có OTP, chuyển hướng về trang process_locker.html
    return redirect(url_for('process_locker'))


def send_otp_deliver(mail, otp_deliver):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "2051010118huyen@ou.edu.vn"
    smtp_password = "nguyenthithuhuyen"

    # Tạo email
    msg = MIMEMultipart()
    msg['From'] = "2051010118huyen@ou.edu.vn"
    msg['To'] = mail
    msg['Subject'] = "Mã OTP_deliver"

    body = f"Mã OTP là: {otp_deliver}\nVui lòng không cung cấp mã này cho bất kì ai. Mã OTP có thời gian sử dụng là 3 tiếng."
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Gửi email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, mail, msg.as_string())  # Sửa từ "mail" thành "email" ở đây
        server.quit()
        return True
    except Exception as e:
        print(f"Lỗi khi gửi email: {str(e)}")
        return False


@app.route('/close_locker', methods=['POST'])
def close_locker():
    cursor = db.cursor()

    # Kiểm tra xem có tủ nào trống (status='off') không
    cursor.execute("SELECT locker_id FROM lockers WHERE status = 'off' LIMIT 1")
    available_locker = cursor.fetchone()

    if available_locker:
        # Nếu có tủ trống, thực hiện các thao tác cần thiết (ví dụ: cập nhật trạng thái, lưu lịch sử)
        locker_id = available_locker[0]

        # Lấy mã OTP_deliver từ bảng otps, sử dụng codeorders từ biến session
        codeorders = session.get('codeorders')
        cursor.execute("SELECT otp_deliver FROM otps WHERE codeorders = %s", (codeorders,))
        otp_deliver = cursor.fetchone()

        if otp_deliver:
            # Truy vấn user_id của người giao hàng (shipper) dựa trên role_id
            cursor.execute("SELECT user_id FROM users WHERE role_id = 3")
            shipper_user_id = cursor.fetchone()

            if shipper_user_id:
                # Lấy địa chỉ email của người giao hàng dựa trên user_id
                cursor.execute("SELECT mail FROM users WHERE user_id = %s", (shipper_user_id[0],))
                shipper_email = cursor.fetchone()

                if shipper_email:
                    otp_deliver = otp_deliver[0]  # Lấy giá trị của mã OTP_deliver

                    # Gửi mã OTP_deliver cho người giao hàng (sử dụng địa chỉ email của người giao hàng)
                    if send_otp_deliver(shipper_email[0], otp_deliver):
                        # Cập nhật user_deliver trong bảng histories
                        cursor.execute(
                            "UPDATE histories SET user_deliver = %s WHERE codeorders = %s",
                            (shipper_user_id[0], codeorders)
                        )

                        # Kiểm tra xem có bất kỳ bản ghi nào có cùng giá trị codeorders
                        cursor.execute("SELECT otpprocessing_id FROM otpprocessing WHERE codeorders = %s",
                                       (codeorders,))
                        otpprocessing_record = cursor.fetchone()

                        if otpprocessing_record:
                            otpprocessing_id = otpprocessing_record[0]

                            # Cập nhật user_id và otp trong bảng otpprocessing
                            cursor.execute(
                                "UPDATE otpprocessing SET user_id = %s, otp = %s WHERE otpprocessing_id = %s",
                                (shipper_user_id[0], otp_deliver, otpprocessing_id)
                            )

                        db.commit()

                        cursor.close()

                        return f"Tủ số {locker_id} đã được đóng và kết thúc. Mã OTP_deliver đã được gửi đến người giao hàng."
                    else:
                        return "Gửi mã OTP_deliver không thành công."
                else:
                    return "Không tìm thấy địa chỉ email của người giao hàng trong cơ sở dữ liệu."
            else:
                return "Không tìm thấy người giao hàng (shipper) có role_id = 3 trong cơ sở dữ liệu."
        else:
            return "Không tìm thấy mã OTP_deliver trong bảng otps."
    else:
        return "Không có tủ trống nào để đóng và kết thúc."

@app.route('/otp_delivery', methods=['GET'])
def otp_delivery():
    return render_template('otp_delivery.html')

@app.route('/validate_otp', methods=['POST'])
def validate_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']

        # Lấy mã OTP_deliver từ biến session
        otp_deliver = session.get('otp_deliver')

        if entered_otp == otp_deliver:
            # Mã OTP đúng, mở tủ để lấy hàng (thực hiện các thao tác cần thiết)

            # Xóa mã OTP_deliver sau khi đã sử dụng
            session.pop('otp_deliver', None)

            # Điều hướng đến trang thông báo tủ đã được mở
            return redirect(url_for('locker_opened'))
        else:
            # Mã OTP không đúng, hiển thị thông báo lỗi
            error_message = "Mã OTP không đúng. Vui lòng thử lại."
            return render_template('otp_delivery.html', error_message=error_message)

@app.route('/locker_opened', methods=['GET'])
def locker_opened():
    return render_template('locker_opened.html')


if __name__ == '__main__':
    app.run()
