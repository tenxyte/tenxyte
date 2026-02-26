# ShopOS — Demo Project for Tenxyte Auth

> **Purpose:** Full-stack demo application showcasing every Tenxyte feature.
> Used as the reference project for tutorials, conference demos, and documentation examples.
>
> **Stack:** Next.js 14 (App Router) + Django REST Framework + Tenxyte Auth

---

## Concept

**ShopOS** is a multi-tenant e-commerce back-office platform where merchants manage their online stores.

Each **Store** is an Organization in Tenxyte. A store has members with different roles (Owner, Manager, Staff). The platform supports multiple authentication methods, strict security policies, and a full RBAC system — making it an ideal canvas to demonstrate every Tenxyte feature in a realistic, relatable context.

---

## User Stories (scope)

### Authentication
- A visitor can **register** with email + password
- A visitor can **log in** via email/password, Google, or GitHub
- A user can log in via a **Magic Link** (passwordless)
- A user can log in with a **Passkey** (WebAuthn / FIDO2)
- A user can enable **2FA (TOTP)** — required for Owners
- A user can verify their phone number via **OTP (SMS)**
- A user can **reset their password** via email
- A user is blocked if they use a **breached password** (HIBP check)
- A user is **locked out** after 5 failed login attempts
- Sessions are limited to **1 concurrent session** per user by default
- Devices are limited to **1 registered device** per user by default

### Profile & Security
- A user can view and update their profile (`/me`)
- A user can view their active sessions and revoke them
- A user can manage their registered Passkeys
- A user can generate and use **backup codes** for 2FA recovery
- All sensitive actions are recorded in the **audit log**

### Stores (Organizations)
- A user can **create a store** (becomes Owner)
- An Owner can **invite members** by email
- An invited user receives an email with a link to join
- An Owner can assign roles: `owner`, `manager`, `staff`
- A Manager can manage products and orders
- A Staff member can only view orders
- An Owner can **remove members** or change their role
- Stores support a **hierarchy**: a store can have sub-stores (e.g. regional branches)

### Products & Orders (app content — minimal)
- A Manager/Owner can **create, edit, delete products** (name, price, stock)
- All roles can **view orders**
- Only Manager/Owner can **update order status**
- Staff cannot access financial reports

### Multi-Application
- The Next.js frontend authenticates via `X-Access-Key` / `X-Access-Secret`
- A second "Mobile App" application is registered to demonstrate multi-app isolation

---

## Tenxyte Features Coverage

| Feature | Where demonstrated |
|---|---|
| **JWT Auth** (access + refresh + rotation) | Login, token refresh on every page load |
| **Email/Password login** | `/login` page |
| **Social Login** (Google, GitHub) | `/login` page — OAuth2 buttons |
| **Magic Link** | `/login` → "Send me a link" |
| **Passkeys / WebAuthn** | Profile → Security → Passkeys |
| **2FA TOTP** | Profile → Security → Enable 2FA |
| **Backup Codes** | Profile → Security → Backup codes |
| **OTP SMS** | Phone verification on registration |
| **Password Reset** | `/forgot-password` flow |
| **Breach Check** | Registration + password change |
| **Account Lockout** | Visible after 5 failed logins |
| **Session Limits** | Profile → Active Sessions |
| **Device Limits** | Profile → Registered Devices |
| **RBAC — Roles** | Store members page (owner/manager/staff) |
| **RBAC — Permissions** | Product/order actions gated by permission |
| **RBAC Decorators** | Django views: `@require_role`, `@require_permission` |
| **Organizations** | Stores = Organizations, sub-stores = hierarchy |
| **Org Invitations** | Invite by email → accept link |
| **Org Memberships** | Member list with role management |
| **Multi-Application** | Web app + Mobile app registered separately |
| **Audit Log** | Admin panel → Audit Log viewer |
| **Rate Limiting** | Visible on login (429 after 5 rapid attempts) |
| **CORS** | Next.js frontend on port 3000 → Django on 8000 |
| **Security Headers** | Enabled in production config |
| **Shortcut Secure Mode** | `TENXYTE_SHORTCUT_SECURE_MODE = 'medium'` in prod settings |
| **Swappable Models** | `CustomUser` with `avatar` + `bio` fields |

---

## Architecture

```
shopOS/
├── backend/                  # Django project
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   └── urls.py
│   ├── accounts/             # Custom User model (extends AbstractUser)
│   │   └── models.py         # CustomUser: avatar, bio
│   ├── stores/               # Store-specific logic (products, orders)
│   │   ├── models.py
│   │   └── views.py
│   └── manage.py
│
└── frontend/                 # Next.js 14 App Router
    ├── app/
    │   ├── (auth)/
    │   │   ├── login/
    │   │   ├── register/
    │   │   ├── forgot-password/
    │   │   └── magic-link/
    │   ├── (dashboard)/
    │   │   ├── dashboard/       # Store overview
    │   │   ├── products/        # Product CRUD
    │   │   ├── orders/          # Order management
    │   │   ├── members/         # Org members + roles
    │   │   └── settings/        # Store settings
    │   └── (profile)/
    │       └── profile/
    │           ├── security/    # 2FA, Passkeys, Sessions, Devices
    │           └── audit-log/
    ├── lib/
    │   ├── tenxyte.ts           # API client (X-Access-Key headers)
    │   └── auth.ts              # JWT token management
    └── middleware.ts            # Route protection (JWT check)
```

---

## Custom User Model

```python
# backend/accounts/models.py
from tenxyte.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True, max_length=500)
    store_count = models.PositiveSmallIntegerField(default=0)

    class Meta(AbstractUser.Meta):
        db_table = 'shopOS_users'
```

```python
# settings/base.py
TENXYTE_USER_MODEL = 'accounts.CustomUser'
AUTH_USER_MODEL = 'accounts.CustomUser'
```

---

## RBAC Setup

### Global Roles (seeded by `tenxyte_seed`)
Used for platform-level access:
- `superadmin` — full platform access
- `admin` — platform admin
- `user` — default authenticated user
- `readonly` — read-only access

### Organization Roles (per-store)
Defined in store setup:
- `owner` — full store control, can invite/remove members, required 2FA
- `manager` — manage products and orders, invite staff
- `staff` — view orders only

### Permission Gates (examples)
```python
# backend/stores/views.py
from tenxyte.decorators import require_permission, require_role

@require_permission('product.create')
def create_product(request): ...

@require_permission('order.update_status')
def update_order(request, order_id): ...

@require_role('owner')
def store_settings(request): ...
```

---

## Settings Configuration

### Development (`settings/development.py`)
```python
TENXYTE_APPLICATION_AUTH_ENABLED = True
TENXYTE_RATE_LIMITING_ENABLED = False   # easier dev
TENXYTE_ACCOUNT_LOCKOUT_ENABLED = False
TENXYTE_BREACH_CHECK_ENABLED = False
TENXYTE_JWT_AUTH_ENABLED = True
TENXYTE_CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.ConsoleBackend'
TENXYTE_EMAIL_BACKEND = 'tenxyte.backends.email.ConsoleBackend'
TENXYTE_MAGIC_LINK_ENABLED = True
TENXYTE_WEBAUTHN_ENABLED = True
TENXYTE_WEBAUTHN_RP_ID = 'localhost'
TENXYTE_ORGANIZATIONS_ENABLED = True
```

### Production (`settings/production.py`)
```python
TENXYTE_SHORTCUT_SECURE_MODE = 'medium'  # enables lockout, breach check, rate limiting, etc.
TENXYTE_CORS_ALLOWED_ORIGINS = ['https://shopOS.example.com']
TENXYTE_WEBAUTHN_RP_ID = 'shopOS.example.com'
TENXYTE_WEBAUTHN_RP_NAME = 'ShopOS'
TENXYTE_MAGIC_LINK_BASE_URL = 'https://shopOS.example.com'
TENXYTE_EMAIL_BACKEND = 'tenxyte.backends.email.SendGridBackend'
TENXYTE_SMS_BACKEND = 'tenxyte.backends.sms.TwilioBackend'
TENXYTE_AUDIT_LOGGING_ENABLED = True
TENXYTE_ORGANIZATIONS_ENABLED = True
```

---

## Next.js API Client

```typescript
// frontend/lib/tenxyte.ts
const TENXYTE_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1/auth/'

const headers = {
  'X-Access-Key': process.env.NEXT_PUBLIC_ACCESS_KEY!,
  'X-Access-Secret': process.env.NEXT_PUBLIC_ACCESS_SECRET!,
  'Content-Type': 'application/json',
}

export async function login(email: string, password: string) {
  const res = await fetch(`${TENXYTE_BASE}/login/email/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ email, password }),
  })
  return res.json()
}

export async function refreshToken(refresh: string) {
  const res = await fetch(`${TENXYTE_BASE}/refresh/`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ refresh }),
  })
  return res.json()
}

export async function getMe(accessToken: string) {
  const res = await fetch(`${TENXYTE_BASE}/me/`, {
    headers: { ...headers, Authorization: `Bearer ${accessToken}` },
  })
  return res.json()
}
```

---

## Key Demo Scenarios (for tutorials/events)

1. **"Register → 2FA → Login"** — full auth flow in 3 minutes
2. **"Magic Link login"** — passwordless in 30 seconds
3. **"Create a store, invite a member, assign a role"** — B2B org flow
4. **"Try to access /products as Staff → 403"** — RBAC in action
5. **"Enter a breached password → rejected"** — security UX
6. **"5 failed logins → lockout screen"** — rate limiting visible
7. **"Register a Passkey → log in with fingerprint"** — WebAuthn wow factor
8. **"Switch to `robust` secure mode in one line"** — Shortcut Secure Mode

---

## Setup Steps

```bash
# Backend
cd backend
pip install tenxyte[all]
python manage.py makemigrations
python manage.py migrate
python manage.py tenxyte_seed        # 4 roles + 41 permissions

# Create the Web Application
python manage.py shell -c "
from tenxyte.models import Application
app, secret = Application.create_application(name='ShopOS Web')
print('Access Key:', app.access_key)
print('Secret:', secret)
"

# Frontend
cd frontend
npm install
cp .env.example .env.local           # fill in Access Key + Secret
npm run dev
```

---

## Deliverables

- [ ] Backend Django project (fully configured)
- [ ] Next.js frontend with all auth flows
- [ ] `README.md` with setup instructions
- [ ] Postman collection for all API endpoints
- [ ] 8 demo scenario scripts (for live demos)
- [ ] Docker Compose (backend + MySQL + frontend)
