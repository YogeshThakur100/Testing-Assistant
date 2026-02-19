from passlib.context import CryptContext # type: ignore 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import os


class EmailUtils:
    sender_email = "gunadhya.ai@gmail.com"
    sender_password = "zdsn pelr qywo uexl"


    @staticmethod
    def send_reset_password_email(email: str, reset_token: str = None, reset_link: str = None):
        """
        Send a password reset email with a clean HTML template
        """
        try:
            # HTML template for reset password email
            html_template = """
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #333333; margin: 0; font-size: 28px;">Password Reset Request</h1>
                        </div>
                        
                        <!-- Main Content -->
                        <div style="margin-bottom: 30px;">
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Hello,
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                We received a request to reset your password. If you didn't make this request, you can ignore this email.
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                To reset your password, click the button below:
                            </p>
                        </div>
                        
                        <!-- Reset Button -->
                        <div style="text-align: center; margin-bottom: 30px;">
                            <a href="{{ reset_link }}/{{reset_token}}" style="display: inline-block; background-color: #007bff; color: #ffffff; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 16px;">
                                Reset Password
                            </a>
                        </div>
                        
                        <!-- Footer Info -->
                        <div style="border-top: 1px solid #eeeeee; padding-top: 20px;">
                            <p style="color: #999999; font-size: 12px; margin: 0 0 10px 0;">
                                This link will expire in 10 minutes.
                            </p>
                            <p style="color: #999999; font-size: 12px; margin: 0;">
                                If you didn't request a password reset, please contact our support team immediately.
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "Password Reset Request"
            message["From"] = EmailUtils.sender_email
            message["To"] = email
            
            # Prepare template with context
            template = Template(html_template)
            html_content = template.render(reset_link=reset_link, reset_token=reset_token)
            
            # Create plain text version
            full_reset_url = f"{reset_link}/{reset_token}" if reset_link and reset_token else (reset_link or "")
            text_version = "Password Reset Request\n\nWe received a request to reset your password.\nClick the link below to reset your password:\n\n" + full_reset_url
            
            # Attach both versions
            part1 = MIMEText(text_version, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Send email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(EmailUtils.sender_email, EmailUtils.sender_password)
                server.sendmail(EmailUtils.sender_email, email, message.as_string())
            
            return {"success": True, "message": "Password reset email sent successfully"}
        
        except Exception as e:
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
