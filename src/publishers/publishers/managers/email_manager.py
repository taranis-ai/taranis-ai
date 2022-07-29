# import smtplib
# import os
# from email import encoders
# from email.mime.base import MIMEBase
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
#
#
# def email_sender():
#     email_user = os.getenv('EMAIL_USER')
#     email_password = os.getenv('EMAIL_PASSWORD')
#     email_send = os.getenv('EMAIL_SEND')
#
#     subject = 'TEST: Sending email from application'
#
#     msg = MIMEMultipart()
#     msg['From'] = email_user
#     msg['To'] = email_send
#     msg['Subject'] = subject
#
#     body = 'Hi there, sending this email from Python!'
#     msg.attach(MIMEText(body, 'plain'))
#
#     filename = 'file.txt'
#     attachment = open(filename, 'rb')
#
#     part = MIMEBase('application', 'octet-stream')
#     part.set_payload(attachment.read())
#     encoders.encode_base64(part)
#     part.add_header('Content-Disposition', 'attachment; filename= ' + filename)
#
#     msg.attach(part)
#     text = msg.as_string()
#
#     server = smtplib.SMTP('smtp.gmail.com', 587)
#     server.starttls()
#     server.login(email_user, email_password)
#     server.sendmail(email_user, email_send, text)
#     server.quit()
