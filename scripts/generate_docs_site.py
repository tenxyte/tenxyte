#!/usr/bin/env python3
"""
Documentation Site Generator — driven by DESIGN_SPEC.json
Principles: Simplicité · Élégance · Modernité · Accessibilité · DRY
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
 
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
 
SPEC_FILE    = project_root / "DESIGN_SPEC.json"
SCHEMA_FILES = [project_root / "openapi_schema_optimized.json",
                project_root / "openapi_schema.json"]
OUTPUT_DIR   = project_root / "docs_site"
SITE_TITLE   = "Tenxyte API"
SITE_LANG    = "fr"
NAV_LINKS: List[Tuple[str, str]] = [
    ("Accueil",          "index.html"),
    ("Référence API",    "api-reference.html"),
    ("Exemples",         "examples.html"),
    ("Authentification", "authentication.html"),
]
METHOD_ORDER = ["get", "post", "put", "patch", "delete"]
 
 
class DocumentationSiteGenerator:
    """Generates a static documentation site driven by DESIGN_SPEC.json."""
 
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.schema: Dict = {}
        self.spec: Dict = self._load_json(SPEC_FILE) if SPEC_FILE.exists() else {}
 
    # ── Orchestration ──────────────────────────────────────────────────
    def generate_site(self) -> bool:
        print("🌐 Generating documentation website…")
        self.schema = self._load_schema()
        if not self.schema:
            return False
        self.output_dir.mkdir(exist_ok=True)
        self._write("index.html",          self._page_index())
        self._write("api-reference.html",  self._page_api_reference())
        self._write("examples.html",       self._page_examples())
        self._write("authentication.html", self._page_authentication())
        self._write("styles.css",          self._css())
        self._write("script.js",           self._js())
        self._write("search.json",         self._search_index())
        print(f"✅ Site generated → {self.output_dir}")
        return True
 
    # ── I/O ────────────────────────────────────────────────────────────
    def _load_schema(self) -> Dict:
        for path in SCHEMA_FILES:
            if path.exists():
                data = self._load_json(path)
                if data:
                    print(f"📋 Schema: {path.name}")
                    return data
        print("❌ No OpenAPI schema found")
        return {}
 
    @staticmethod
    def _load_json(path: Path) -> Dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ {path.name}: {e}")
            return {}
 
    def _write(self, filename: str, content: str):
        (self.output_dir / filename).write_text(content, encoding="utf-8")
 
    # ── Single HTML shell — DRY ────────────────────────────────────────
    def _page(self, title: str, description: str, body: str, active: str = "", search_data: str = "null") -> str:
        nav = "".join(
            '<a href="{h}" class="nav__link{a}" {c}>{l}</a>'.format(
                h=href, l=label,
                a=" nav__link--active" if href == active else "",
                c='aria-current="page"' if href == active else "")
            for label, href in NAV_LINKS)
        v = self.schema.get("info", {}).get("version", "1.0")
        lines = [
            "<!DOCTYPE html>",
            f'<html lang="{SITE_LANG}">',
            "<head>",
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'  <title>{title} — {SITE_TITLE}</title>',
            f'  <meta name="description" content="{description}">',
            "  <link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>\">",
            '  <link rel="preconnect" href="https://fonts.googleapis.com">',
            '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
            '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">',
            '  <link rel="stylesheet" href="styles.css">',
            "</head><body>",
            '  <a href="#main" class="skip-link">Aller au contenu</a>',
            '  <header class="nav" role="banner"><div class="nav__inner">',
            f'    <a href="index.html" class="nav__brand" aria-label="{SITE_TITLE}">',
            '      <span class="nav__logo" aria-hidden="true">⚡</span>',
            f'      <span class="nav__name">{SITE_TITLE}</span></a>',
            f'    <nav role="navigation" aria-label="Navigation principale">{nav}</nav>',
            '    <div role="search"><div class="search">',
            '      <input class="search__input" type="search" id="searchInput"',
            '             placeholder="Rechercher…" aria-label="Rechercher" autocomplete="off">',
            '      <div class="search__results" id="searchResults" role="listbox" hidden></div>',
            '    </div></div>',
            '    <button class="btn-icon" id="themeToggle" aria-label="Basculer le thème">',
            '      <span aria-hidden="true">🌙</span></button>',
            '    <a href="https://github.com/tenxyte/tenxyte" class="btn-cta" target="_blank" rel="noopener" aria-label="GitHub">GitHub</a>',
            '  </div></header>',
            f'  <main id="main" role="main">{body}</main>',
            '  <footer class="footer" role="contentinfo"><div class="footer__inner">',
            f'    <p>© 2025 {SITE_TITLE} · v{v}</p>',
            '    <nav aria-label="Liens utiles">',
            '      <a href="http://localhost:8000/api/docs/" target="_blank" rel="noopener">Swagger UI</a>',
            '      <a href="http://localhost:8000/api/redoc/" target="_blank" rel="noopener">ReDoc</a>',
            '      <a href="https://github.com/tenxyte/tenxyte" target="_blank" rel="noopener">GitHub</a>',
            '    </nav></div></footer>',
            f'  <script>window.__SEARCH_DATA__ = {search_data};</script>',
            '  <script src="script.js"></script>',
            "</body></html>",
        ]
        return "\n".join(lines)
 
    # ── Reusable components — DRY, no inline styles ────────────────────
    def _method_badge(self, m: str) -> str:
        u = m.upper()
        return f'<span class="badge badge--{m.lower()}" aria-label="HTTP {u}">{u}</span>'
 
    def _status_badge(self, code: str) -> str:
        cls = "2xx" if code.startswith("2") else ("4xx" if code.startswith("4") else "5xx")
        return f'<span class="status status--{cls}">{code}</span>'
 
    def _code_block(self, lang: str, code: str, label: str = "") -> str:
        d = label or lang
        e = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (f'<div class="code-block" role="region" aria-label="Code {d}">'
                f'<div class="code-block__header">'
                f'<span class="code-block__lang">{d}</span>'
                f'<button class="code-block__copy" aria-label="Copier" data-copy>Copier</button>'
                f'</div><pre class="code-block__pre"><code class="lang-{lang}">{e}</code></pre></div>')
 
    def _tab_group(self, gid: str, tabs: List[Tuple[str, str, str]]) -> str:
        btns = "".join(
            '<button class="tabs__btn{a}" role="tab" aria-selected="{s}" '
            'aria-controls="tab-{g}-{t}" id="btn-{g}-{t}">{l}</button>'.format(
                a=" tabs__btn--active" if i == 0 else "",
                s="true" if i == 0 else "false",
                g=gid, t=tid, l=label)
            for i, (tid, label, _) in enumerate(tabs))
        panels = "".join(
            '<div class="tabs__panel{a}" role="tabpanel" id="tab-{g}-{t}" '
            'aria-labelledby="btn-{g}-{t}"{h}>{c}</div>'.format(
                a=" tabs__panel--active" if i == 0 else "",
                g=gid, t=tid,
                h="" if i == 0 else " hidden",
                c=content)
            for i, (tid, _, content) in enumerate(tabs))
        return f'<div class="tabs" role="tablist">{btns}</div>{panels}'
 
    def _resolve_ref(self, ref_str: str) -> Dict:
        parts = ref_str.replace("#/", "").split("/")
        res = self.schema
        for p in parts:
            res = res.get(p, {})
        return res

    def _resolve_schema(self, schema: Any, seen: set = None) -> Any:
        if seen is None:
            seen = set()
        if not isinstance(schema, dict):
            return schema
        if "$ref" in schema:
            ref_path = schema["$ref"]
            if ref_path in seen:
                return {} 
            seen.add(ref_path)
            return self._resolve_schema(self._resolve_ref(ref_path), seen)
        
        resolved = {}
        for k, v in schema.items():
            if isinstance(v, dict):
                resolved[k] = self._resolve_schema(v, seen.copy())
            elif isinstance(v, list):
                resolved[k] = [self._resolve_schema(item, seen.copy()) for item in v]
            else:
                resolved[k] = v
        return resolved

    def _generate_mock_from_schema(self, schema: Any, seen: set = None) -> Any:
        if seen is None:
            seen = set()
        if not isinstance(schema, dict):
            return schema
            
        if "$ref" in schema:
            ref_path = schema["$ref"]
            if ref_path in seen:
                return {}
            seen.add(ref_path)
            return self._generate_mock_from_schema(self._resolve_ref(ref_path), seen)
            
        schema_type = schema.get("type", "object")
        if schema_type == "object":
            props = schema.get("properties", {})
            return {k: self._generate_mock_from_schema(v, seen.copy()) for k, v in props.items()}
        elif schema_type == "array":
            items = schema.get("items", {})
            return [self._generate_mock_from_schema(items, seen.copy())]
        elif schema_type == "string":
            if schema.get("format") == "date-time":
                return "2023-01-01T00:00:00Z"
            if schema.get("example"):
                return schema.get("example")
            return "string"
        elif schema_type == "integer":
            return schema.get("example", 0)
        elif schema_type == "number":
            return schema.get("example", 0.0)
        elif schema_type == "boolean":
            return schema.get("example", True)
        return {}

    def _params_table(self, params: List[Dict]) -> str:
        if not params:
            return ""
        resolved_params = [self._resolve_schema(p) if "$ref" in p else p for p in params]
        rows = "".join(
            '<tr><td><code>{n}</code>{r}</td>'
            '<td><code class="type">{t}</code></td>'
            '<td class="muted">{loc}</td><td>{d}</td></tr>'.format(
                n=p.get("name", ""),
                r='<span class="required" aria-label="Requis">*</span>' if p.get("required") else "",
                t=p.get("schema", {}).get("type", p.get("type", "string")),
                loc=p.get("in", ""),
                d=p.get("description", ""))
            for p in resolved_params)
        return ('<div class="table-wrap"><table class="params-table" aria-label="Paramètres">'
                '<thead><tr><th scope="col">Nom</th><th scope="col">Type</th>'
                '<th scope="col">Emplacement</th><th scope="col">Description</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')
 
    def _card(self, icon: str, title: str, body: str) -> str:
        return (f'<div class="card"><div class="card__icon" aria-hidden="true">{icon}</div>'
                f'<h3 class="card__title">{title}</h3><p class="card__body">{body}</p></div>')
 
    def _stat(self, value: str, label: str) -> str:
        return (f'<div class="stat"><span class="stat__value">{value}</span>'
                f'<span class="stat__label">{label}</span></div>')
 
    def _alert(self, kind: str, text: str) -> str:
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        return (f'<div class="alert alert--{kind}" role="alert">'
                f'<span aria-hidden="true">{icons.get(kind, "")}</span> {text}</div>')
 
    def _section(self, title: str, body: str, id_: str = "") -> str:
        a = f' id="{id_}"' if id_ else ""
        return f'<section class="section"{a}><h2 class="section__title">{title}</h2>{body}</section>'
 
    def _extract_example(self, ct_spec: Dict) -> Any:
        ex = ct_spec.get("examples", {})
        if ex:
            return next(iter(ex.values()), {}).get("value")
        if "example" in ct_spec:
            return ct_spec["example"]
        
        schema = ct_spec.get("schema")
        if schema:
            return self._generate_mock_from_schema(schema)
        return None
 
    @staticmethod
    def _slug(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
 
    # ── Pages ──────────────────────────────────────────────────────────
    def _page_index(self) -> str:
        paths   = self.schema.get("paths", {})
        schemas = self.schema.get("components", {}).get("schemas", {})
        info    = self.schema.get("info", {})
        stats = "".join([
            self._stat(str(len(paths)),   "Endpoints"),
            self._stat(str(len(schemas)), "Schémas"),
            self._stat("8",               "Méthodes d'auth"),
            self._stat("100%",            "Couverture"),
        ])
        cards = "".join([
            self._card("🔐", "Authentification avancée",
                       "JWT, 2FA TOTP, Magic Links, WebAuthn, Social OAuth"),
            self._card("🏢", "Multi-tenant",
                       "Organisations hiérarchiques, RBAC, rôles par organisation"),
            self._card("🛡️", "Sécurité & RGPD",
                       "Conformité RGPD, gestion des appareils, audit complet"),
            self._card("📊", "Dashboard admin",
                       "Statistiques temps réel, métriques de sécurité"),
        ])
        quick = self._code_block(
            "bash",
            'curl -X POST .../api/v1/auth/login/email/ \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"email\":\"user@example.com\",\"password\":\"motdepasse\"}'\n\n"
            'curl .../api/v1/auth/me/ \\\n  -H "Authorization: Bearer <access_token>"',
            "Démarrage rapide — cURL")
        alert = self._alert(
            "info",
            'Documentation interactive : <a href="http://localhost:8000/api/docs/">Swagger UI</a>'
            ' · <a href="http://localhost:8000/api/redoc/">ReDoc</a>')
        sec_features  = self._section("Fonctionnalités", '<div class="cards-grid">' + cards + '</div>', "features")
        sec_quickstart = self._section("Démarrage rapide", quick, "quickstart")
        body = (
            f'<div class="hero"><div class="hero__inner">'
            f'<span class="hero__badge">v{info.get("version", "1.0")}</span>'
            f'<h1 class="hero__title">{info.get("title", SITE_TITLE)}</h1>'
            f'<p class="hero__subtitle">{info.get("description", "Documentation API complète.")}</p>'
            f'<div class="hero__actions">'
            f'<a href="api-reference.html" class="btn btn--primary">Référence API</a>'
            f'<a href="examples.html" class="btn btn--secondary">Exemples</a>'
            f'<a href="authentication.html" class="btn btn--ghost">Authentification</a>'
            f'</div></div></div>'
            f'<div class="container">'
            f'<div class="stats-bar" aria-label="Statistiques API">{stats}</div>'
            f'{sec_features}'
            f'{sec_quickstart}'
            f'{alert}'
            f'</div>')
        return self._page(
            "Accueil",
            info.get("description", "Documentation API Tenxyte"),
            body, "index.html", self._search_index())
 
    def _page_api_reference(self) -> str:
        categories = self._categorize(self.schema.get("paths", {}))
        sidebar_items = "".join(
            f'<li><a class="sidebar__link" href="#cat-{self._slug(cat)}">{cat}'
            f'<span class="sidebar__count">{len(items)}</span></a></li>'
            for cat, items in categories.items())
        sidebar = (f'<nav class="sidebar" aria-label="Catégories">'
                   f'<ul class="sidebar__list">{sidebar_items}</ul></nav>')
        parts = []
        for cat, items in categories.items():
            eps = "".join(self._endpoint_block(p, pi) for p, pi in items)
            parts.append(
                f'<section class="api-category" id="cat-{self._slug(cat)}">'
                f'<h2 class="api-category__title">{cat}</h2>{eps}</section>')
        body = (f'<div class="api-layout">{sidebar}'
                f'<div class="api-content"><div class="container">'
                f'<h1 class="page-title">Référence API</h1>{"".join(parts)}'
                f'</div></div></div>')
        return self._page(
            "Référence API", "Référence complète de tous les endpoints",
            body, "api-reference.html", self._search_index())
 
    def _endpoint_block(self, path: str, path_item: Dict) -> str:
        parts = []
        for method in METHOD_ORDER:
            op = path_item.get(method)
            if not op:
                continue
            op_id   = op.get("operationId", f"{method}-{path}")
            summary = op.get("summary", "")
            desc    = op.get("description", "")
            tags    = "".join(f'<span class="tag">{t}</span>' for t in op.get("tags", []))
            params  = self._params_table(op.get("parameters", []))
            req = ""
            for ct, cs in op.get("requestBody", {}).get("content", {}).items():
                ex = self._extract_example(cs) or cs.get("schema")
                if ex:
                    req += self._code_block(
                        "json", json.dumps(ex, indent=2, ensure_ascii=False),
                        f"Corps — {ct}")
            resps = []
            for code, resp in op.get("responses", {}).items():
                rb = ""
                for ct, cs in resp.get("content", {}).items():
                    ex = self._extract_example(cs)
                    if ex:
                        rb += self._code_block(
                            "json", json.dumps(ex, indent=2, ensure_ascii=False), ct)
                resps.append(
                    f'<div class="response-item">{self._status_badge(str(code))} '
                    f'<span>{resp.get("description", "")}</span>{rb}</div>')
            inner = ""
            if desc:
                inner += f'<p class="op__desc">{desc}</p>'
            if params:
                inner += f'<h4 class="op__subtitle">Paramètres</h4>{params}'
            if req:
                inner += f'<h4 class="op__subtitle">Corps de la requête</h4>{req}'
            if resps:
                inner += (f'<h4 class="op__subtitle">Réponses</h4>'
                          f'<div class="responses">{"".join(resps)}</div>')
            sid = self._slug(op_id)
            parts.append(
                f'<div class="endpoint" id="op-{sid}">'
                f'<button class="endpoint__header" aria-expanded="false"'
                f' aria-controls="op-body-{sid}">'
                f'{self._method_badge(method)}'
                f'<code class="endpoint__path">{path}</code>'
                f'<span class="endpoint__summary">{summary}</span>'
                f'<span class="endpoint__tags">{tags}</span>'
                f'<span class="endpoint__chevron" aria-hidden="true">›</span>'
                f'</button>'
                f'<div class="endpoint__body" id="op-body-{sid}" hidden>{inner}</div>'
                f'</div>')
        return "".join(parts)
 
    def _page_examples(self) -> str:
        examples = [
            ("auth",   "Authentification",    self._ex_auth()),
            ("multi",  "Multi-tenant",        self._ex_multitenant()),
            ("errors", "Gestion des erreurs", self._ex_errors()),
            ("twofa",  "2FA",                 self._ex_2fa()),
            ("orgs",   "Organisations",       self._ex_organizations()),
        ]
        sections = "".join(
            self._section(label, self._tab_group(tid, [
                ("py",   "Python",     self._code_block("python",     py,   "Python")),
                ("js",   "JavaScript", self._code_block("javascript", js,   "JavaScript")),
                ("curl", "cURL",       self._code_block("bash",       curl, "cURL")),
            ]))
            for tid, label, (py, js, curl) in examples)
        body = (f'<div class="container">'
                f'<h1 class="page-title">Exemples de code</h1>{sections}</div>')
        return self._page(
            "Exemples", "Exemples pratiques d'intégration de l'API Tenxyte",
            body, "examples.html", self._search_index())
 
    def _page_authentication(self) -> str:
        jwt_c = self._code_block(
            "bash",
            'curl .../me/ \\\n  -H "Authorization: Bearer eyJ..."',
            "Requête authentifiée")
        tfa_c = self._code_block(
            "bash",
            'curl -X POST .../2fa/setup/ -H "Authorization: Bearer <token>"\n\n'
            'curl -X POST .../2fa/confirm/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            "  -d '{\"code\":\"123456\"}'",
            "Configuration 2FA")
        social_c = self._code_block(
            "bash",
            'curl -X POST .../social/google/ \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"id_token\":\"<google_id_token>\"}'\n\n"
            '# Or initiate OAuth flow:',
            "Authentification sociale")
        magic_c = self._code_block(
            "bash",
            'curl -X POST .../magic-link/request/ \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"email\":\"user@example.com\"}'\n\n"
            'curl -X POST .../magic-link/verify/ \\\n'
            "  -d '{\"token\":\"<token_from_email>\"}'\n",
            "Magic Link")
        webauthn_c = self._code_block(
            "bash",
            '# 1. Register a passkey\n'
            'curl -X POST .../webauthn/register/begin/ -H "Authorization: Bearer <token>"\n\n'
            '# 2. Complete registration with browser response\n'
            'curl -X POST .../webauthn/register/complete/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            "  -d '{...credential_response...}'\n\n"
            '# 3. Authenticate with passkey\n'
            'curl -X POST .../webauthn/authenticate/begin/\n'
            'curl -X POST .../webauthn/authenticate/complete/ -d \'...resp...\'',
            "WebAuthn / Passkeys")
        org_c = self._code_block(
            "bash",
            'curl .../organizations/members/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            '  -H "X-Org-Slug: acme-corp"',
            "Requête multi-tenant")
        sections = [
            self._section(
                "JWT — Flux d'authentification",
                '<ol class="steps">'
                '<li>Envoyez vos identifiants à <code>/login/email/</code></li>'
                '<li>Recevez <code>access</code> + <code>refresh</code> tokens</li>'
                '<li>Incluez : <code>Authorization: Bearer &lt;token&gt;</code></li>'
                f'<li>Rafraîchissez avant expiration via <code>/refresh/</code></li></ol>{jwt_c}',
                "jwt"),
            self._section(
                "Authentification à deux facteurs (2FA)",
                self._alert("info", "Activez la 2FA pour renforcer la sécurité.") + tfa_c,
                "twofa"),
            self._section(
                "Authentification sociale (OAuth)",
                self._alert("info", "Supporte Google OAuth2 via id_token ou flux de redirection.") + social_c,
                "social"),
            self._section(
                "Magic Link — Connexion sans mot de passe",
                '<p>Envoyez un lien de connexion par email — aucun mot de passe requis.</p>' + magic_c,
                "magic-link"),
            self._section(
                "WebAuthn / Passkeys (FIDO2)",
                self._alert("success", "Standard le plus sécurisé — résistant au phishing.") + webauthn_c,
                "webauthn"),
            self._section(
                "Multi-tenant — En-tête X-Org-Slug",
                f'<p>Ajoutez <code>X-Org-Slug</code> pour le contexte organisation.</p>{org_c}',
                "multitenant"),
            self._section(
                "Bonnes pratiques",
                '<ul class="checklist">'
                '<li>Utilisez toujours HTTPS</li>'
                '<li>Ne stockez jamais les tokens dans <code>localStorage</code></li>'
                '<li>Implémentez le rafraîchissement automatique</li>'
                '<li>Activez la 2FA pour les opérations sensibles</li>'
                '<li>Gérez le rate limiting avec un backoff exponentiel</li>'
                '<li>Déconnectez-vous proprement pour invalider les tokens</li>'
                '</ul>',
                "best-practices"),
        ]
        body = (f'<div class="container">'
                f'<h1 class="page-title">Guide d\'authentification</h1>'
                f'{"".join(sections)}</div>')
        return self._page(
            "Authentification", "Guide complet des méthodes d'authentification",
            body, "authentication.html", self._search_index())
 
    # ── Code examples ──────────────────────────────────────────────────
    def _ex_auth(self) -> Tuple[str, str, str]:
        py = (
            "import requests\n\n"
            'resp = requests.post(".../login/email/", json={\n'
            '    "email": "user@example.com", "password": "motdepasse"})\n'
            'access = resp.json()["access"]\n'
            'profile = requests.get(".../me/",\n'
            '    headers={"Authorization": f"Bearer {access}"}).json()\n'
            "print(profile)")
        js = (
            'const { access } = await fetch("/api/v1/auth/login/email/", {\n'
            '  method: "POST",\n'
            '  headers: { "Content-Type": "application/json" },\n'
            '  body: JSON.stringify({ email: "user@example.com", password: "motdepasse" }),\n'
            '}).then(r => r.json());\n'
            'const profile = await fetch("/api/v1/auth/me/", {\n'
            '  headers: { Authorization: `Bearer ${access}` },\n'
            '}).then(r => r.json());\nconsole.log(profile);')
        curl = (
            'curl -X POST .../login/email/ \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"email\":\"user@example.com\",\"password\":\"motdepasse\"}'\n\n"
            'curl .../me/ -H "Authorization: Bearer <access_token>"')
        return py, js, curl
 
    def _ex_multitenant(self) -> Tuple[str, str, str]:
        py = (
            "import requests\n\n"
            'headers = {"Authorization": "Bearer <token>", "X-Org-Slug": "acme-corp"}\n'
            'members = requests.get(".../organizations/members/", headers=headers).json()\n'
            'print(f"{len(members)} membres")')
        js = (
            'const members = await fetch("/api/v1/auth/organizations/members/", {\n'
            '  headers: { Authorization: "Bearer <token>", "X-Org-Slug": "acme-corp" },\n'
            '}).then(r => r.json());\nconsole.log(members.length, "membres");')
        curl = (
            'curl .../organizations/members/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            '  -H "X-Org-Slug: acme-corp"')
        return py, js, curl
 
    def _ex_errors(self) -> Tuple[str, str, str]:
        py = (
            "import requests, time\n\n"
            "def api_call(url, **kw):\n"
            "    for _ in range(3):\n"
            "        r = requests.post(url, **kw)\n"
            "        if r.status_code == 429:\n"
            '            time.sleep(int(r.headers.get("Retry-After", 5)))\n'
            "            continue\n"
            "        r.raise_for_status()\n"
            "        return r.json()\n"
            '    raise RuntimeError("Rate limit dépassé")')
        js = (
            "async function apiCall(url, opts={}, retries=3) {\n"
            "  const r = await fetch(url, opts);\n"
            "  if (r.status === 429 && retries > 0) {\n"
            "    await new Promise(res => setTimeout(res,\n"
            '      Number(r.headers.get("Retry-After") ?? 5) * 1000));\n'
            "    return apiCall(url, opts, retries - 1);\n"
            "  }\n"
            "  if (!r.ok) { const e = await r.json();"
            " throw Object.assign(new Error(e.error), e); }\n"
            "  return r.json();\n}")
        curl = (
            "# Format d'erreur : { \"error\": \"...\", \"code\": \"MACHINE_CODE\" }\n"
            'curl -i -X POST .../login/email/ \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"email\":\"bad@example.com\",\"password\":\"wrong\"}'")
        return py, js, curl
 
    def _ex_2fa(self) -> Tuple[str, str, str]:
        py = (
            "import requests\n\n"
            'headers = {"Authorization": "Bearer <token>"}\n'
            'setup = requests.post(".../2fa/setup/", headers=headers).json()\n'
            'requests.post(".../2fa/confirm/", headers=headers, json={"code": "123456"})')
        js = (
            'const { qr_code } = await fetch(".../2fa/setup/", {\n'
            '  method: "POST", headers: { Authorization: "Bearer <token>" }\n'
            '}).then(r => r.json());\n'
            'await fetch(".../2fa/confirm/", {\n'
            '  method: "POST",\n'
            '  headers: { Authorization: "Bearer <token>", "Content-Type": "application/json" },\n'
            '  body: JSON.stringify({ code: "123456" }),\n});')
        curl = (
            'curl -X POST .../2fa/setup/ -H "Authorization: Bearer <token>"\n\n'
            'curl -X POST .../2fa/confirm/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            "  -d '{\"code\":\"123456\"}'")
        return py, js, curl
 
    def _ex_organizations(self) -> Tuple[str, str, str]:
        py = (
            "import requests\n\n"
            'headers = {"Authorization": "Bearer <token>"}\n'
            '# Create an organisation\n'
            'org = requests.post(".../organizations/", headers=headers,\n'
            '    json={"name": "Acme Corp", "slug": "acme-corp"}).json()\n\n'
            '# Invite a member\n'
            'requests.post(".../organizations/members/add/", headers=headers,\n'
            '    json={"email": "colleague@example.com", "role": "member"})')
        js = (
            'const org = await fetch("/api/v1/auth/organizations/", {\n'
            '  method: "POST",\n'
            '  headers: { Authorization: "Bearer <token>", "Content-Type": "application/json" },\n'
            '  body: JSON.stringify({ name: "Acme Corp", slug: "acme-corp" }),\n'
            '}).then(r => r.json());\n\n'
            '// Get org tree\n'
            'const tree = await fetch("/api/v1/auth/organizations/tree/", {\n'
            '  headers: { Authorization: "Bearer <token>", "X-Org-Slug": "acme-corp" },\n'
            '}).then(r => r.json());\nconsole.log(tree);')
        curl = (
            'curl -X POST .../organizations/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\"name\":\"Acme Corp\",\"slug\":\"acme-corp\"}' \n\n"
            'curl .../organizations/tree/ \\\n'
            '  -H "Authorization: Bearer <token>" \\\n'
            '  -H "X-Org-Slug: acme-corp"')
        return py, js, curl
 
    # ── Categorize paths ───────────────────────────────────────────────
    def _categorize(self, paths: Dict) -> Dict:
        order = ["Authentification", "Utilisateur", "Organisations",
                 "Sécurité", "Applications", "Admin", "Autre"]
        cats  = {k: [] for k in order}
        rules = [
            (["login", "register", "refresh", "logout", "google", "social",
               "magic", "webauthn", "password", "otp", "2fa"], "Authentification"),
            (["/me/"],                                           "Utilisateur"),
            (["organizations", "org-roles"],                    "Organisations"),
            (["sessions", "devices", "audit", "blacklisted",
               "refresh-token"],                                "Sécurité"),
            (["applications"],                                  "Applications"),
            (["admin", "dashboard", "gdpr", "deletion"],        "Admin"),
        ]
        for path, path_item in paths.items():
            methods = {m: op for m, op in path_item.items() if m in METHOD_ORDER}
            if not methods:
                continue
            assigned = "Autre"
            for keywords, cat in rules:
                if any(k in path for k in keywords):
                    assigned = cat
                    break
            cats[assigned].append((path, path_item))
        return {k: v for k, v in cats.items() if v}
 
    # ── Search index ───────────────────────────────────────────────────
    def _search_index(self) -> str:
        pages = [{"title": label, "url": href, "content": label}
                 for label, href in NAV_LINKS]
        for path, path_item in self.schema.get("paths", {}).items():
            for method in METHOD_ORDER:
                op = path_item.get(method)
                if op:
                    pages.append({
                        "title":   op.get("summary", path),
                        "url":     f"api-reference.html#op-{self._slug(op.get('operationId', path))}",
                        "content": op.get("description", op.get("summary", "")),
                    })
        return json.dumps({"pages": pages}, ensure_ascii=False, indent=2)
 
    # ── CSS ────────────────────────────────────────────────────────────
    def _css(self) -> str:
        # ── Read all design tokens from DESIGN_SPEC.json ──────────────────
        t        = self.spec.get("tokens", {})
        color    = t.get("color", {})
        brand    = color.get("brand", {})
        neutral  = color.get("neutral", {})
        semantic = color.get("semantic", {})
        method   = color.get("method", {})
        surface  = color.get("surface", {})
        code_c   = color.get("code", {})
        text_c   = color.get("text", {})
        border_c = color.get("border", {})
        font     = t.get("typography", {}).get("font", {})
        radius   = t.get("radius", {})
        shadow   = t.get("shadow", {})
        trans    = t.get("transition", {})
        layout   = t.get("layout", {})
        dark     = self.spec.get("generation", {}).get("dark_mode", {})

        # ── Resolve token values with spec-compliant fallbacks ─────────────
        primary       = brand.get("primary",        "#6366f1")
        primary_hover = brand.get("primary-hover",  "#4f46e5")
        primary_sub   = brand.get("primary-subtle", "#eef2ff")
        surf          = surface.get("raised",   neutral.get("50",  "#f8fafc"))
        overlay       = surface.get("overlay",  neutral.get("100", "#f1f5f9"))
        txt           = text_c.get("primary",   neutral.get("900", "#0f172a"))
        txt_sec       = text_c.get("secondary", neutral.get("600", "#475569"))
        muted         = text_c.get("muted",     neutral.get("400", "#94a3b8"))
        link          = text_c.get("link", primary)
        border        = border_c.get("default", neutral.get("200", "#e2e8f0"))
        border_sub    = border_c.get("subtle",  neutral.get("100", "#f1f5f9"))
        code_bg       = code_c.get("bg",   "#0f172a")
        code_txt      = code_c.get("text", "#e2e8f0")
        code_kw       = code_c.get("keyword", "#a78bfa")
        code_str      = code_c.get("string",  "#34d399")
        success       = semantic.get("success", "#10b981")
        warning       = semantic.get("warning", "#f59e0b")
        error         = semantic.get("error",   "#ef4444")
        info          = semantic.get("info",    "#3b82f6")
        c_get         = method.get("GET",    "#10b981")
        c_post        = method.get("POST",   primary)
        c_put         = method.get("PUT",    "#f59e0b")
        c_patch       = method.get("PATCH",  "#f97316")
        c_delete      = method.get("DELETE", "#ef4444")
        f_sans        = font.get("sans", "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif")
        f_mono        = font.get("mono", "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace")
        r_sm          = radius.get("sm",   "0.375rem")
        r_md          = radius.get("md",   "0.5rem")
        r_lg          = radius.get("lg",   "0.75rem")
        r_full        = radius.get("full", "9999px")
        sh_sm         = shadow.get("sm", "0 1px 2px 0 rgb(0 0 0 / 0.05)")
        sh_md         = shadow.get("md", "0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05)")
        sh_xl         = shadow.get("xl", "0 20px 25px -5px rgb(0 0 0 / 0.07), 0 8px 10px -6px rgb(0 0 0 / 0.05)")
        tr_fast       = trans.get("fast",   "150ms ease")
        tr_normal     = trans.get("normal", "250ms ease")
        nav_h         = layout.get("nav-height",    "64px")
        sidebar_w     = layout.get("sidebar-width", "280px")
        page_max      = layout.get("page-max",      "1440px")
        # Dark mode overrides
        dk_bg      = dark.get("surface.page",    "#0f172a")
        dk_surf    = dark.get("surface.raised",  "#1e293b")
        dk_overlay = dark.get("surface.overlay", "#334155")
        dk_txt     = dark.get("text.primary",    "#f1f5f9")
        dk_muted   = dark.get("text.secondary",  "#94a3b8")
        dk_border  = dark.get("border.default",  "#334155")

        return f"""/* Tenxyte API Docs — generated from DESIGN_SPEC.json */
:root {{
  --c-primary:      {primary};
  --c-primary-h:    {primary_hover};
  --c-primary-sub:  {primary_sub};
  --c-bg:           #ffffff;
  --c-surface:      {surf};
  --c-overlay:      {overlay};
  --c-border:       {border};
  --c-border-sub:   {border_sub};
  --c-text:         {txt};
  --c-text-sec:     {txt_sec};
  --c-muted:        {muted};
  --c-link:         {link};
  --c-code-bg:      {code_bg};
  --c-code-text:    {code_txt};
  --c-code-kw:      {code_kw};
  --c-code-str:     {code_str};
  --c-success:      {success};
  --c-warning:      {warning};
  --c-error:        {error};
  --c-info:         {info};
  --c-get:          {c_get};
  --c-post:         {c_post};
  --c-put:          {c_put};
  --c-patch:        {c_patch};
  --c-delete:       {c_delete};
  --font-sans:      {f_sans};
  --font-mono:      {f_mono};
  --radius-sm:      {r_sm};
  --radius:         {r_md};
  --radius-lg:      {r_lg};
  --radius-full:    {r_full};
  --shadow:         {sh_sm};
  --shadow-md:      {sh_md};
  --shadow-xl:      {sh_xl};
  --nav-h:          {nav_h};
  --sidebar-w:      {sidebar_w};
  --container:      {page_max};
  --transition:     {tr_fast};
  --transition-n:   {tr_normal};
}}

/* Dark mode — CSS-first via prefers-color-scheme (spec requirement) */
@media (prefers-color-scheme: dark) {{
  :root {{
    --c-bg:       {dk_bg};
    --c-surface:  {dk_surf};
    --c-overlay:  {dk_overlay};
    --c-border:   {dk_border};
    --c-text:     {dk_txt};
    --c-muted:    {dk_muted};
    --c-code-bg:  #0d1117;
  }}
}}
/* Dark mode — manual toggle overrides prefers-color-scheme */
[data-theme="dark"] {{
  --c-bg:       {dk_bg};
  --c-surface:  {dk_surf};
  --c-overlay:  {dk_overlay};
  --c-border:   {dk_border};
  --c-text:     {dk_txt};
  --c-muted:    {dk_muted};
  --c-code-bg:  #0d1117;
}}
[data-theme="light"] {{
  --c-bg:       #ffffff;
  --c-surface:  {surf};
  --c-border:   {border};
  --c-text:     {txt};
  --c-muted:    {muted};
  --c-code-bg:  {code_bg};
}}
 
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
 
body {{
  font-family: var(--font-sans);
  font-size: 1rem;
  line-height: 1.6;
  color: var(--c-text);
  background: var(--c-bg);
  transition: background var(--transition), color var(--transition);
}}
 
/* ── Accessibility ── */
.skip-link {{
  position: absolute; top: -100%; left: 1rem;
  background: var(--c-primary); color: #fff;
  padding: .5rem 1rem; border-radius: var(--radius-sm);
  font-weight: 600; text-decoration: none; z-index: 9999;
}}
.skip-link:focus {{ top: 1rem; }}
 
*:focus-visible {{
  outline: 2px solid var(--c-primary);
  outline-offset: 2px;
}}
 
/* ── Nav ── */
.nav {{
  position: sticky; top: 0; z-index: 100;
  height: var(--nav-h);
  background: var(--c-bg);
  border-bottom: 1px solid var(--c-border);
  backdrop-filter: blur(8px);
}}
.nav__inner {{
  display: flex; align-items: center; gap: 1.5rem;
  max-width: var(--container); margin: 0 auto;
  padding: 0 1.5rem; height: 100%;
}}
.nav__brand {{
  display: flex; align-items: center; gap: .5rem;
  text-decoration: none; font-weight: 700; font-size: 1.1rem;
  color: var(--c-text); flex-shrink: 0;
}}
.nav__logo {{ font-size: 1.4rem; }}
.nav__name {{ color: var(--c-primary); }}
nav[aria-label="Navigation principale"] {{
  display: flex; gap: .25rem; flex: 1;
}}
.nav__link {{
  padding: .4rem .75rem; border-radius: var(--radius-sm);
  text-decoration: none; font-size: .9rem; font-weight: 500;
  color: var(--c-muted); transition: color var(--transition), background var(--transition);
}}
.nav__link:hover {{ color: var(--c-text); background: var(--c-surface); }}
.nav__link--active {{ color: var(--c-primary); background: color-mix(in srgb, var(--c-primary) 10%, transparent); }}
 
/* ── Search ── */
.search {{ position: relative; }}
.search__input {{
  padding: .4rem .9rem; border: 1px solid var(--c-border);
  border-radius: 20px; font-size: .875rem;
  background: var(--c-surface); color: var(--c-text);
  width: 200px; transition: width var(--transition), border-color var(--transition);
}}
.search__input:focus {{ width: 280px; border-color: var(--c-primary); outline: none; }}
.search__results {{
  position: absolute; top: calc(100% + .5rem); right: 0;
  width: 320px; background: var(--c-bg);
  border: 1px solid var(--c-border); border-radius: var(--radius);
  box-shadow: var(--shadow-md); z-index: 200;
}}
.search__result {{
  display: block; padding: .75rem 1rem; text-decoration: none;
  color: var(--c-text); font-size: .875rem;
  border-bottom: 1px solid var(--c-border);
  transition: background var(--transition);
}}
.search__result:hover {{ background: var(--c-surface); }}
.search__result:last-child {{ border-bottom: none; }}
 
/* ── Theme toggle ── */
.btn-icon {{
  background: none; border: 1px solid var(--c-border);
  border-radius: var(--radius-sm); padding: .35rem .6rem;
  cursor: pointer; font-size: 1rem; flex-shrink: 0;
  color: var(--c-text); transition: background var(--transition);
}}
.btn-icon:hover {{ background: var(--c-surface); }}
 
/* ── Hero ── */
.hero {{
  background: linear-gradient(135deg, var(--c-primary) 0%, #7c3aed 100%);
  color: #fff; padding: 5rem 1.5rem;
}}
.hero__inner {{
  max-width: 700px; margin: 0 auto; text-align: center;
}}
.hero__badge {{
  display: inline-block; background: rgba(255,255,255,.2);
  padding: .2rem .75rem; border-radius: 20px;
  font-size: .8rem; font-weight: 600; margin-bottom: 1.25rem;
}}
.hero__title {{ font-size: clamp(2rem, 5vw, 3rem); font-weight: 700; margin-bottom: 1rem; }}
.hero__subtitle {{ font-size: 1.1rem; opacity: .9; margin-bottom: 2rem; }}
.hero__actions {{ display: flex; gap: .75rem; justify-content: center; flex-wrap: wrap; }}
 
/* ── Buttons ── */
.btn {{
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .6rem 1.25rem; border-radius: var(--radius-sm);
  font-weight: 600; font-size: .9rem; text-decoration: none;
  transition: all var(--transition); cursor: pointer; border: none;
}}
.btn--primary  {{ background: #fff; color: var(--c-primary); }}
.btn--primary:hover  {{ background: #f0f4ff; }}
.btn--secondary {{ background: rgba(255,255,255,.15); color: #fff; border: 1px solid rgba(255,255,255,.4); }}
.btn--secondary:hover {{ background: rgba(255,255,255,.25); }}
.btn--ghost {{ background: transparent; color: #fff; border: 1px solid rgba(255,255,255,.4); }}
.btn--ghost:hover {{ background: rgba(255,255,255,.1); }}
.btn-cta {{
  display: inline-flex; align-items: center; gap: .35rem;
  padding: .4rem 1rem; border-radius: var(--radius-sm);
  background: var(--c-primary); color: #fff;
  text-decoration: none; font-size: .85rem; font-weight: 600;
  transition: background var(--transition); flex-shrink: 0;
}}
.btn-cta:hover {{ background: var(--c-primary-h); }}
 
/* ── Container ── */
.container {{ max-width: var(--container); margin: 0 auto; padding: 2rem 1.5rem; }}
 
/* ── Stats bar ── */
.stats-bar {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem; margin: 2rem 0;
}}
.stat {{
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius); padding: 1.25rem; text-align: center;
}}
.stat__value {{ display: block; font-size: 2rem; font-weight: 700; color: var(--c-primary); }}
.stat__label {{ font-size: .8rem; color: var(--c-muted); font-weight: 500; }}
 
/* ── Section ── */
.section {{ margin: 2.5rem 0; }}
.section__title {{
  font-size: 1.4rem; font-weight: 700; margin-bottom: 1.25rem;
  padding-bottom: .5rem; border-bottom: 2px solid var(--c-border);
}}
 
/* ── Cards ── */
.cards-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
}}
.card {{
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius); padding: 1.5rem;
  transition: box-shadow var(--transition), transform var(--transition);
}}
.card:hover {{ box-shadow: var(--shadow-md); transform: translateY(-2px); }}
.card__icon {{ font-size: 2rem; margin-bottom: .75rem; }}
.card__title {{ font-size: 1rem; font-weight: 600; margin-bottom: .5rem; }}
.card__body {{ font-size: .875rem; color: var(--c-muted); }}
 
/* ── Alert ── */
.alert {{
  display: flex; align-items: flex-start; gap: .75rem;
  padding: 1rem 1.25rem; border-radius: var(--radius);
  margin: 1.25rem 0; font-size: .9rem;
}}
.alert--info    {{ background: color-mix(in srgb, var(--c-info) 10%, transparent);    border-left: 4px solid var(--c-info); }}
.alert--success {{ background: color-mix(in srgb, var(--c-success) 10%, transparent); border-left: 4px solid var(--c-success); }}
.alert--warning {{ background: color-mix(in srgb, var(--c-warning) 10%, transparent); border-left: 4px solid var(--c-warning); }}
.alert--error   {{ background: color-mix(in srgb, var(--c-error) 10%, transparent);   border-left: 4px solid var(--c-error); }}
.alert a {{ color: var(--c-primary); }}
 
/* ── Code block ── */
.code-block {{
  border: 1px solid var(--c-border); border-radius: var(--radius);
  overflow: hidden; margin: 1rem 0;
}}
.code-block__header {{
  display: flex; justify-content: space-between; align-items: center;
  padding: .5rem 1rem; background: var(--c-surface);
  border-bottom: 1px solid var(--c-border);
}}
.code-block__lang {{ font-family: var(--font-mono); font-size: .8rem; color: var(--c-muted); }}
.code-block__copy {{
  background: var(--c-primary); color: #fff; border: none;
  padding: .2rem .65rem; border-radius: var(--radius-sm);
  font-size: .75rem; cursor: pointer; transition: background var(--transition);
}}
.code-block__copy:hover {{ background: var(--c-primary-h); }}
.code-block__copy.copied {{ background: var(--c-success); }}
.code-block__pre {{
  margin: 0; padding: 1rem 1.25rem; overflow-x: auto;
  background: var(--c-code-bg);
  color: var(--c-code-text);
  font-family: var(--font-mono); font-size: .85rem; line-height: 1.6;
}}
 
/* ── Tabs ── */
.tabs {{
  display: flex; border-bottom: 1px solid var(--c-border);
  margin-bottom: 0; overflow-x: auto;
}}
.tabs__btn {{
  padding: .65rem 1.1rem; border: none; background: none;
  font-size: .875rem; font-weight: 500; cursor: pointer;
  color: var(--c-muted); border-bottom: 2px solid transparent;
  transition: color var(--transition), border-color var(--transition);
  white-space: nowrap;
}}
.tabs__btn:hover {{ color: var(--c-text); }}
.tabs__btn--active {{ color: var(--c-primary); border-bottom-color: var(--c-primary); }}
.tabs__panel {{ display: none; }}
.tabs__panel--active {{ display: block; }}
 
/* ── Table ── */
.table-wrap {{ overflow-x: auto; margin: 1rem 0; }}
.params-table {{ width: 100%; border-collapse: collapse; font-size: .875rem; }}
.params-table th, .params-table td {{
  padding: .65rem .9rem; text-align: left;
  border-bottom: 1px solid var(--c-border);
}}
.params-table th {{ background: var(--c-surface); font-weight: 600; }}
.params-table code {{ font-family: var(--font-mono); font-size: .8rem; }}
.required {{ color: var(--c-error); margin-left: .2rem; font-weight: 700; }}
.muted {{ color: var(--c-muted); }}
.type {{ color: var(--c-primary); }}
 
/* ── API layout ── */
.api-layout {{
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: calc(100vh - var(--nav-h));
}}
.sidebar {{
  position: sticky; top: var(--nav-h);
  height: calc(100vh - var(--nav-h));
  overflow-y: auto; padding: 1.5rem 1rem;
  border-right: 1px solid var(--c-border);
  background: var(--c-surface);
}}
.sidebar__list {{ list-style: none; }}
.sidebar__link {{
  display: flex; justify-content: space-between; align-items: center;
  padding: .45rem .75rem; border-radius: var(--radius-sm);
  text-decoration: none; font-size: .875rem; color: var(--c-muted);
  transition: background var(--transition), color var(--transition);
  margin-bottom: .15rem;
}}
.sidebar__link:hover {{ background: var(--c-border); color: var(--c-text); }}
.sidebar__count {{
  background: var(--c-border); color: var(--c-muted);
  font-size: .7rem; padding: .1rem .4rem; border-radius: 10px;
}}
.api-content {{ min-width: 0; }}
 
/* ── API category ── */
.api-category {{ padding: 2rem 0; border-bottom: 1px solid var(--c-border); }}
.api-category__title {{
  font-size: 1.3rem; font-weight: 700; margin-bottom: 1.25rem;
  padding: 0 1.5rem;
}}
 
/* ── Endpoint ── */
.endpoint {{
  border: 1px solid var(--c-border); border-radius: var(--radius);
  margin: .75rem 1.5rem; overflow: hidden;
}}
.endpoint__header {{
  display: flex; align-items: center; gap: .75rem;
  width: 100%; padding: .85rem 1rem;
  background: var(--c-bg); border: none; cursor: pointer;
  text-align: left; transition: background var(--transition);
}}
.endpoint__header:hover {{ background: var(--c-surface); }}
.endpoint__header[aria-expanded="true"] {{ background: var(--c-surface); }}
.endpoint__path {{ font-family: var(--font-mono); font-size: .85rem; flex: 1; }}
.endpoint__summary {{ font-size: .875rem; color: var(--c-muted); }}
.endpoint__tags {{ display: flex; gap: .3rem; flex-wrap: wrap; }}
.endpoint__chevron {{
  font-size: 1.2rem; color: var(--c-muted); margin-left: auto;
  transition: transform var(--transition);
}}
.endpoint__header[aria-expanded="true"] .endpoint__chevron {{ transform: rotate(90deg); }}
.endpoint__body {{ padding: 1.25rem; border-top: 1px solid var(--c-border); }}
 
/* ── Badges ── */
.badge {{
  padding: .2rem .55rem; border-radius: var(--radius-sm);
  font-size: .75rem; font-weight: 700; flex-shrink: 0;
}}
.badge--get    {{ background: color-mix(in srgb, var(--c-get) 15%, transparent);    color: var(--c-get); }}
.badge--post   {{ background: color-mix(in srgb, var(--c-post) 15%, transparent);   color: var(--c-post); }}
.badge--put    {{ background: color-mix(in srgb, var(--c-put) 15%, transparent);    color: var(--c-put); }}
.badge--patch  {{ background: color-mix(in srgb, var(--c-patch) 15%, transparent);  color: var(--c-patch); }}
.badge--delete {{ background: color-mix(in srgb, var(--c-delete) 15%, transparent); color: var(--c-delete); }}
 
.status {{ padding: .15rem .5rem; border-radius: var(--radius-sm); font-size: .8rem; font-weight: 600; }}
.status--2xx {{ background: color-mix(in srgb, var(--c-success) 15%, transparent); color: var(--c-success); }}
.status--4xx {{ background: color-mix(in srgb, var(--c-warning) 15%, transparent); color: var(--c-warning); }}
.status--5xx {{ background: color-mix(in srgb, var(--c-error) 15%, transparent);   color: var(--c-error); }}
 
.tag {{
  background: var(--c-surface); border: 1px solid var(--c-border);
  padding: .1rem .45rem; border-radius: 10px; font-size: .7rem; color: var(--c-muted);
}}
 
/* ── Op details ── */
.op__desc {{ color: var(--c-muted); font-size: .9rem; margin-bottom: 1rem; }}
.op__subtitle {{ font-size: .85rem; font-weight: 600; color: var(--c-muted); text-transform: uppercase; letter-spacing: .05em; margin: 1.25rem 0 .5rem; }}
.responses {{ display: flex; flex-direction: column; gap: .5rem; }}
.response-item {{ display: flex; align-items: flex-start; gap: .75rem; flex-wrap: wrap; }}
 
/* ── Page title ── */
.page-title {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 2rem; padding-top: .5rem; }}
 
/* ── Steps / checklist ── */
.steps {{ padding-left: 1.5rem; }}
.steps li {{ margin-bottom: .5rem; }}
.checklist {{ list-style: none; }}
.checklist li {{ padding: .4rem 0; padding-left: 1.5rem; position: relative; }}
.checklist li::before {{ content: "✓"; position: absolute; left: 0; color: var(--c-success); font-weight: 700; }}
 
/* ── Footer ── */
.footer {{
  background: var(--c-surface); border-top: 1px solid var(--c-border);
  padding: 1.5rem 0; margin-top: 4rem;
}}
.footer__inner {{
  max-width: var(--container); margin: 0 auto; padding: 0 1.5rem;
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: 1rem; font-size: .875rem; color: var(--c-muted);
}}
.footer__inner nav {{ display: flex; gap: 1.5rem; }}
.footer__inner a {{ color: var(--c-muted); text-decoration: none; transition: color var(--transition); }}
.footer__inner a:hover {{ color: var(--c-primary); }}
 
/* ── Responsive ── */
@media (max-width: 768px) {{
  .api-layout {{ grid-template-columns: 1fr; }}
  .sidebar {{ position: static; height: auto; border-right: none; border-bottom: 1px solid var(--c-border); }}
  nav[aria-label="Navigation principale"] {{ display: none; }}
  .search__input {{ width: 160px; }}
  .search__input:focus {{ width: 200px; }}
  .hero {{ padding: 3rem 1rem; }}
  .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
}}
"""
 
    # ── JavaScript ─────────────────────────────────────────────────────
    def _js(self) -> str:
        return """/* Tenxyte API Docs — script.js */
'use strict';
 
// ── Theme toggle ──────────────────────────────────────────────────────
const THEME_KEY = 'tenxyte-theme';
const root = document.documentElement;
const themeBtn = document.getElementById('themeToggle');
 
function applyTheme(theme) {
  root.setAttribute('data-theme', theme);
  if (themeBtn) themeBtn.querySelector('span').textContent = theme === 'dark' ? '☀️' : '🌙';
}
 
(function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(preferred);
})();
 
if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(THEME_KEY, next);
  });
}
 
// ── Endpoint accordion ────────────────────────────────────────────────
document.querySelectorAll('.endpoint__header').forEach(btn => {
  btn.addEventListener('click', () => {
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!expanded));
    const body = document.getElementById(btn.getAttribute('aria-controls'));
    if (body) body.hidden = expanded;
  });
});
 
// ── Tabs ──────────────────────────────────────────────────────────────
document.querySelectorAll('.tabs').forEach(tablist => {
  tablist.querySelectorAll('.tabs__btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const panelId = btn.getAttribute('aria-controls');
      const group   = btn.closest('.tabs').parentElement;
 
      tablist.querySelectorAll('.tabs__btn').forEach(b => {
        b.classList.remove('tabs__btn--active');
        b.setAttribute('aria-selected', 'false');
      });
      group.querySelectorAll('.tabs__panel').forEach(p => {
        p.classList.remove('tabs__panel--active');
        p.hidden = true;
      });
 
      btn.classList.add('tabs__btn--active');
      btn.setAttribute('aria-selected', 'true');
      const panel = document.getElementById(panelId);
      if (panel) { panel.classList.add('tabs__panel--active'); panel.hidden = false; }
    });
  });
});
 
// ── Copy code ─────────────────────────────────────────────────────────
document.querySelectorAll('[data-copy]').forEach(btn => {
  btn.addEventListener('click', () => {
    const code = btn.closest('.code-block').querySelector('code');
    if (!code) return;
    navigator.clipboard.writeText(code.textContent).then(() => {
      btn.textContent = 'Copié !';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'Copier'; btn.classList.remove('copied'); }, 2000);
    }).catch(() => {});
  });
});
 
// ── Search ────────────────────────────────────────────────────────────
const searchInput   = document.getElementById('searchInput');
const searchResults = document.getElementById('searchResults');
let searchData = null;
 
function loadSearchData() {
  if (searchData) return searchData;
  searchData = (typeof window.__SEARCH_DATA__ !== 'undefined' && window.__SEARCH_DATA__)
    ? window.__SEARCH_DATA__
    : { pages: [] };
  return searchData;
}
 
if (searchInput) {
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) { searchResults.hidden = true; return; }
    const data = loadSearchData();
    const hits = data.pages.filter(p =>
      p.title.toLowerCase().includes(q) || p.content.toLowerCase().includes(q)
    ).slice(0, 8);
    if (!hits.length) { searchResults.hidden = true; return; }
    searchResults.innerHTML = hits.map(p =>
      `<a class="search__result" href="${p.url}">${p.title}</a>`
    ).join('');
    searchResults.hidden = false;
  });
 
  document.addEventListener('click', e => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target))
      searchResults.hidden = true;
  });
 
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault(); searchInput.focus();
    }
    if (e.key === 'Escape') { searchResults.hidden = true; searchInput.blur(); }
  });
}
 
// ── Smooth scroll for anchor links ────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
  });
});
"""
 
 
def main():
    generator = DocumentationSiteGenerator()
    success = generator.generate_site()
    if success:
        print(f"\n📁 Location: {generator.output_dir}")
        print("📋 Files: index.html, api-reference.html, examples.html, "
              "authentication.html, styles.css, script.js, search.json")
        sys.exit(0)
    else:
        print("\n❌ Failed to generate documentation site")
        sys.exit(1)


if __name__ == "__main__":
    main()
