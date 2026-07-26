import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import get_settings


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_password_reset(self, recipient: str, token: str) -> None:
        if not all(
            [
                self.settings.smtp_host,
                self.settings.smtp_user,
                self.settings.smtp_password,
                self.settings.smtp_from,
            ]
        ):
            raise RuntimeError("SMTP configuration is incomplete")

        reset_url = (
            f"{self.settings.frontend_url.rstrip('/')}/reset-password"
            f"?token={quote(token)}"
        )

        message = EmailMessage()
        message["Subject"] = "Redefinição de senha — JJ AI Platform"
        message["From"] = self.settings.smtp_from
        message["To"] = recipient
        message.set_content(
            "Recebemos uma solicitação para redefinir sua senha da JJ AI Platform.\n\n"
            f"Acesse o link abaixo em até {self.settings.password_reset_expire_minutes} minutos:\n"
            f"{reset_url}\n\n"
            "Caso você não tenha solicitado a alteração, ignore esta mensagem."
        )
        message.add_alternative(
            f"""
            <html>
              <body style="font-family:Arial,sans-serif;background:#020617;color:#e2e8f0;padding:32px">
                <div style="max-width:560px;margin:auto;background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:32px">
                  <h1 style="font-size:22px;margin:0 0 16px">Redefinição de senha</h1>
                  <p style="line-height:1.6;color:#cbd5e1">Recebemos uma solicitação para redefinir sua senha da JJ AI Platform.</p>
                  <p style="line-height:1.6;color:#cbd5e1">O link expira em {self.settings.password_reset_expire_minutes} minutos.</p>
                  <p style="margin:28px 0">
                    <a href="{reset_url}" style="background:#3b82f6;color:white;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700">Criar nova senha</a>
                  </p>
                  <p style="font-size:13px;line-height:1.6;color:#94a3b8">Caso você não tenha solicitado a alteração, ignore esta mensagem.</p>
                </div>
              </body>
            </html>
            """,
            subtype="html",
        )

        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=15,
            ) as smtp:
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
                smtp.send_message(message)
            return

        with smtplib.SMTP(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=15,
        ) as smtp:
            smtp.starttls()
            smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)
