from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: bool = True
    email_enabled: bool = False
    critical_only: bool = True
    email_address: EmailStr | None = None


class NotificationPreferenceResponse(NotificationPreferenceUpdate):
    model_config = ConfigDict(from_attributes=True)


class NotificationTestEmailResponse(BaseModel):
    status: str
    recipient: EmailStr
    sent_at: dt.datetime
