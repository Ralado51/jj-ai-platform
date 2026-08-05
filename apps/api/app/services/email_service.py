import smtplib
from email.message import EmailMessage
from html import escape
from urllib.parse import quote

from app.core.config import get_settings


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_password_reset(self, recipient: str, token: str) -> None:
        reset_url = (
            f"{self.settings.frontend_url.rstrip('/')}/reset-password"
            f"?token={quote(token)}"
        )
        message = EmailMessage()
        message["Subject"] = "Redefinição de senha — JJ AI Platform"
        message.set_content(
            "Recebemos uma solicitação para redefinir sua senha da JJ AI Platform.\n\n"
            f"Acesse o link abaixo em até {self.settings.password_reset_expire_minutes} minutos:\n"
            f"{reset_url}\n\n"
            "Caso você não tenha solicitado a alteração, ignore esta mensagem."
        )
        message.add_alternative(
            f"""
            <html><body style="font-family:Arial,sans-serif;background:#020617;color:#e2e8f0;padding:32px">
              <div style="max-width:560px;margin:auto;background:#0f172a;border:1px solid #1e293b;border-radius:16px;padding:32px">
                <h1 style="font-size:22px;margin:0 0 16px">Redefinição de senha</h1>
                <p style="line-height:1.6;color:#cbd5e1">Recebemos uma solicitação para redefinir sua senha da JJ AI Platform.</p>
                <p style="line-height:1.6;color:#cbd5e1">O link expira em {self.settings.password_reset_expire_minutes} minutos.</p>
                <p style="margin:28px 0"><a href="{reset_url}" style="background:#3b82f6;color:white;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700">Criar nova senha</a></p>
                <p style="font-size:13px;line-height:1.6;color:#94a3b8">Caso você não tenha solicitado a alteração, ignore esta mensagem.</p>
              </div>
            </body></html>
            """,
            subtype="html",
        )
        self._send(recipient, message)

    def send_notification_test(self, recipient: str) -> None:
        settings_url = f"{self.settings.frontend_url.rstrip('/')}/settings/notifications"
        message = EmailMessage()
        message["Subject"] = "Teste de notificações — JJ AI Platform"
        message.set_content(
            "Este é um e-mail de teste da JJ AI Platform.\n\n"
            "O canal de notificações por e-mail está configurado corretamente.\n\n"
            f"Gerencie suas preferências em: {settings_url}"
        )
        message.add_alternative(
            f"""
            <html><body style="font-family:Arial,sans-serif;background:#020617;color:#e2e8f0;padding:32px">
              <div style="max-width:620px;margin:auto;background:#0f172a;border:1px solid #1d4ed8;border-radius:16px;padding:32px">
                <p style="margin:0 0 8px;color:#93c5fd;font-weight:700">TESTE DE NOTIFICAÇÃO</p>
                <h1 style="font-size:22px;margin:0 0 16px">Canal de e-mail configurado</h1>
                <p style="line-height:1.6;color:#cbd5e1">Este e-mail confirma que a JJ AI Platform consegue enviar notificações para este endereço.</p>
                <p style="margin:28px 0"><a href="{settings_url}" style="background:#2563eb;color:white;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700">Ver preferências</a></p>
              </div>
            </body></html>
            """,
            subtype="html",
        )
        self._send(recipient, message)

    def send_workflow_health_regression(
        self,
        *,
        recipient: str,
        workflow_name: str,
        previous_score: int,
        current_score: int,
        delta: int,
        workflow_id: str,
    ) -> None:
        analytics_url = f"{self.settings.frontend_url.rstrip('/')}/workflow-analytics?workflow_id={quote(workflow_id)}"
        subject = f"Regressão crítica em {workflow_name} — JJ AI Platform"
        text = (
            f"O Health Score do workflow {workflow_name} caiu de {previous_score} para {current_score} "
            f"({delta} pontos).\n\nAnalise os detalhes em: {analytics_url}"
        )
        message = EmailMessage()
        message["Subject"] = subject
        message.set_content(text)
        message.add_alternative(
            f"""
            <html><body style="font-family:Arial,sans-serif;background:#020617;color:#e2e8f0;padding:32px">
              <div style="max-width:620px;margin:auto;background:#0f172a;border:1px solid #7f1d1d;border-radius:16px;padding:32px">
                <p style="margin:0 0 8px;color:#fca5a5;font-weight:700">ALERTA CRÍTICO</p>
                <h1 style="font-size:22px;margin:0 0 16px">Regressão em {escape(workflow_name)}</h1>
                <p style="line-height:1.6;color:#cbd5e1">O Health Score caiu de <strong>{previous_score}</strong> para <strong>{current_score}</strong> ({delta} pontos).</p>
                <p style="margin:28px 0"><a href="{analytics_url}" style="background:#dc2626;color:white;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700">Ver Workflow Analytics</a></p>
              </div>
            </body></html>
            """,
            subtype="html",
        )
        self._send(recipient, message)

    def send_ai_budget_critical(
        self,
        *,
        recipient: str,
        budget_name: str,
        usage_percent: float,
        current_spend: str,
        monthly_limit: str,
    ) -> None:
        budgets_url = f"{self.settings.frontend_url.rstrip('/')}/analytics/budgets"
        safe_name = escape(budget_name)
        message = EmailMessage()
        message["Subject"] = f"Budget crítico: {budget_name} — JJ AI Platform"
        message.set_content(
            f"O budget {budget_name} atingiu {usage_percent:.2f}% do limite mensal.\n\n"
            f"Consumo atual: US$ {current_spend}\n"
            f"Limite mensal: US$ {monthly_limit}\n\n"
            f"Revise o consumo em: {budgets_url}"
        )
        message.add_alternative(
            f"""
            <html><body style="font-family:Arial,sans-serif;background:#020617;color:#e2e8f0;padding:32px">
              <div style="max-width:620px;margin:auto;background:#0f172a;border:1px solid #7f1d1d;border-radius:16px;padding:32px">
                <p style="margin:0 0 8px;color:#fca5a5;font-weight:700">BUDGET CRÍTICO</p>
                <h1 style="font-size:22px;margin:0 0 16px">{safe_name}</h1>
                <p style="line-height:1.6;color:#cbd5e1">O consumo atingiu <strong>{usage_percent:.2f}%</strong> do limite mensal.</p>
                <div style="margin:20px 0;padding:16px;background:#020617;border-radius:10px">
                  <p style="margin:0 0 8px;color:#cbd5e1">Consumo atual: <strong>US$ {escape(current_spend)}</strong></p>
                  <p style="margin:0;color:#cbd5e1">Limite mensal: <strong>US$ {escape(monthly_limit)}</strong></p>
                </div>
                <p style="margin:28px 0"><a href="{budgets_url}" style="background:#dc2626;color:white;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700">Ver AI Budgets</a></p>
              </div>
            </body></html>
            """,
            subtype="html",
        )
        self._send(recipient, message)

    def _send(self, recipient: str, message: EmailMessage) -> None:
        if not all([self.settings.smtp_host, self.settings.smtp_user, self.settings.smtp_password, self.settings.smtp_from]):
            raise RuntimeError("SMTP configuration is incomplete")
        message["From"] = self.settings.smtp_from
        message["To"] = recipient
        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
                smtp.login(self.settings.smtp_user, self.settings.smtp_password)
                smtp.send_message(message)
            return
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(self.settings.smtp_user, self.settings.smtp_password)
            smtp.send_message(message)
