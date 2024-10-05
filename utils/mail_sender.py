import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

# 載入 .env 檔案中的變量
load_dotenv()

def send_email(receiver_email, subject, content):
    sender_email = os.getenv("SENDER_EMAIL")  # 寄件者電子郵件
    app_password = os.getenv("APP_PASSWORD")  # 應用程式密碼

    # 設定郵件主題與內容
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    # 寫入郵件內容
    part = MIMEText(content, "plain")
    message.attach(part)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            print("郵件發送成功！")
    except Exception as e:
        print(f"郵件發送失敗: {e}")
