# python script for sending SMTP configuration with Oracle Cloud Infrastructure Email Delivery
# if using ubuntu 20.04, there could be an issue with SSL security level being too high
# fix available at https://bugs.launchpad.net/ubuntu/+source/openssl/+bug/1864689
# In /etc/ssl/openssl.cnf, add this line before the start of the file:
#
#  openssl_conf = default_conf
#
# At the end of the file, add these lines:
#
#  [default_conf]
#  ssl_conf = ssl_sect
#
#  [ssl_sect]
#  system_default = system_default_sect
#
#  [system_default_sect]
#  CipherString = DEFAULT:@SECLEVEL=1
#
# This will bring down the SSL security level to the former level of 1.
#
import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Replace sender@example.com with your "From" address.
# This address must be verified.
SENDER = 'noreply@nodomain.com'
SENDERNAME = 'noreply'

# Replace recipient@example.com with a "To" address. If your account
# is still in the sandbox, this address must be verified.
RECIPIENT = 'zampasoft@hotmail.com'

# Replace the USERNAME_SMTP value with your Email Delivery SMTP username.
USERNAME_SMTP = 'ocid1.user.oc1..aaaaaaaar2rnkot6dywkfe3cq6vzz4xkzgwx4vi242gxxxkelcpjpphmnxka@ocid1.tenancy.oc1..aaaaaaaaj3t5zo3drea6j5iag2hxl4nrthjuuyybrw4wdcwsmag7kwjnqmgq.3x.com'

# Replace the PASSWORD_SMTP value with your Email Delivery SMTP password.
PASSWORD_SMTP = 'VJDbwvo41$NtYvHs(c{C'

# If you're using Email Delivery in a different region, replace the HOST value with an SMTP endpoint. Use port 25 or 587 to connect to the SMTP endpoint.
HOST = "smtp.email.eu-amsterdam-1.oci.oraclecloud.com"
PORT = 587

# The subject line of the email.
SUBJECT = 'Email Delivery Test (Python smtplib)'

# The email body for recipients with non-HTML email clients.
BODY_TEXT = ("Email Delivery Test\r\n"
             "This email was sent through the Email Delivery SMTP "
             "Interface using the Python smtplib package."
             )

# The HTML body of the email.
BODY_HTML = """<html>
<head></head>
<body>
  <h1>Email Delivery SMTP Email Test</h1>
  <p>This email was sent with Email Delivery using the
    <a href='https://www.python.org/'>Python</a>
    <a href='https://docs.python.org/3/library/smtplib.html'>
    smtplib</a> library.</p>
</body>
</html>"""

# Create message container - the correct MIME type is multipart/alternative.
msg = MIMEMultipart('alternative')
msg['Subject'] = SUBJECT
msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
msg['To'] = RECIPIENT

# Record the MIME types of both parts - text/plain and text/html.
part1 = MIMEText(BODY_TEXT, 'plain')
part2 = MIMEText(BODY_HTML, 'html')

# Attach parts into message container.
# According to RFC 2046, the last part of a multipart message, in this case
# the HTML message, is best and preferred.
msg.attach(part1)
msg.attach(part2)

# Try to send the message.
try:
    server = smtplib.SMTP(HOST, PORT)
    # server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    # smtplib docs recommend calling ehlo() before & after starttls()
    server.ehlo()
    server.login(USERNAME_SMTP, PASSWORD_SMTP)
    server.sendmail(SENDER, RECIPIENT, msg.as_string())
    server.close()
# Display an error message if something goes wrong.
except Exception as e:
    print("Error: ", e)
else:
    print("Email successfully sent!")
