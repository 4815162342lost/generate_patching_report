def send_mail(email_adr, email_from, smtp_server, filename, today, description):
    '''Function for send e-mail'''
    import smtplib
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email import encoders
    import io
    import termcolor
    attachment_text = description + today.strftime("%B")
    msg = MIMEMultipart()
    msg['Subject'] = 'Patching_list'
    msg['From'] = email_from
    msg['To'] = email_adr
    f = io.StringIO(attachment_text)
    part = MIMEText(f.getvalue())
    msg.attach(part)
    part = MIMEBase('application', "octet-stream")
    part.set_payload(open(filename, "rb").read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(part)
    try:
        s = smtplib.SMTP(smtp_server)
        s.sendmail(msg['From'], msg['To'], msg.as_string())
        s.quit()
    except Exception as e:
        termcolor.cprint('Error occured during sendig e-mail. Exception: ', color='red', on_color='on_white')
        print(e)
        return None
