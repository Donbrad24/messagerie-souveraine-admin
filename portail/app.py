import os
import re
import json
import secrets
from datetime import datetime
from urllib.parse import quote

import requests
from flask import Flask, request, render_template_string

HS = os.environ.get("SYNAPSE_URL", "http://synapse:8008")
SERVER = os.environ.get("SERVER_NAME", "localhost")
SUPER_USER = os.environ["SUPER_ADMIN_USER"]
SUPER_PASS = os.environ["SUPER_ADMIN_PASSWORD"]
NOM_OK = re.compile(r"^[a-z0-9._-]{3,32}$")

with open("/app/ministeres.json", encoding="utf-8") as f:
    MINISTERES = json.load(f)

app = Flask(__name__)


def enc(valeur):
    return quote(valeur, safe="")


def login(user, password):
    try:
        r = requests.post(
            f"{HS}/_matrix/client/v3/login",
            json={
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": user},
                "password": password,
                "initial_device_display_name": "portail-comptes",
            },
            timeout=10,
        )
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    return r.json().get("access_token")


def logout(token):
    try:
        requests.post(f"{HS}/_matrix/client/v3/logout",
                      headers={"Authorization": f"Bearer {token}"}, timeout=10)
    except requests.RequestException:
        pass


def est_admin_espace(token, user_id, espace):
    r = requests.get(
        f"{HS}/_matrix/client/v3/rooms/{enc(espace)}/state/m.room.power_levels",
        headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if r.status_code != 200:
        return False
    niveaux = r.json()
    niveau = niveaux.get("users", {}).get(user_id, niveaux.get("users_default", 0))
    return niveau >= 100


def journal(evenement, admin, ministere, agent=""):
    print(f"{datetime.now().isoformat(timespec='seconds')} | {evenement} | "
          f"admin={admin} | ministere={ministere} | agent={agent}", flush=True)


def traiter(f):
    cle = f.get("ministere", "")
    admin = f.get("admin_user", "").strip().lower()
    mdp = f.get("admin_password", "")
    agent = f.get("nouvel_agent", "").strip().lower()
    nom = f.get("nom_affiche", "").strip()[:60] or agent

    if cle not in MINISTERES or not NOM_OK.match(admin) or not NOM_OK.match(agent):
        return {"ok": False, "msg": "Champs invalides (3 à 32 caractères : minuscules, chiffres, . _ -)."}

    espace = MINISTERES[cle]["espace"]
    admin_id = f"@{admin}:{SERVER}"
    agent_id = f"@{agent}:{SERVER}"

    tok_admin = login(admin, mdp)
    if not tok_admin or not est_admin_espace(tok_admin, admin_id, espace):
        if tok_admin:
            logout(tok_admin)
        journal("REFUS", admin, cle, agent)
        return {"ok": False, "msg": "Identifiants invalides ou droits insuffisants pour ce ministère."}

    tok_super = login(SUPER_USER, SUPER_PASS)
    try:
        if not tok_super:
            return {"ok": False, "msg": "Erreur interne du portail."}
        h = {"Authorization": f"Bearer {tok_super}"}
        url = f"{HS}/_synapse/admin/v2/users/{enc(agent_id)}"

        if requests.get(url, headers=h, timeout=10).status_code != 404:
            return {"ok": False, "msg": "Ce nom d'utilisateur existe déjà."}

        mdp_temp = secrets.token_urlsafe(9)
        r = requests.put(url, headers=h, timeout=10,
                         json={"password": mdp_temp, "admin": False, "displayname": nom})
        if r.status_code not in (200, 201):
            return {"ok": False, "msg": "Échec de la création du compte."}

        inv = requests.post(
            f"{HS}/_matrix/client/v3/rooms/{enc(espace)}/invite",
            headers={"Authorization": f"Bearer {tok_admin}"},
            json={"user_id": agent_id}, timeout=10)
        journal("CREATION", admin, cle, agent)
        if inv.status_code != 200:
            return {"ok": True, "msg": f"Compte {agent_id} créé, mais l'invitation a échoué. Mot de passe temporaire : {mdp_temp}"}
        return {"ok": True, "msg": f"Compte {agent_id} créé et invité dans l'espace. Mot de passe temporaire (affiché une seule fois) : {mdp_temp}"}
    finally:
        logout(tok_admin)
        if tok_super:
            logout(tok_super)


PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>Gestion des comptes - Messagerie souveraine</title>
<style>
 body{font-family:sans-serif;max-width:520px;margin:40px auto;padding:0 16px}
 label{display:block;margin-top:12px}
 input,select{width:100%;padding:8px;box-sizing:border-box}
 button{margin-top:16px;padding:10px 16px}
 .ok{background:#e6f4ea;padding:12px;margin-top:16px}
 .ko{background:#fdecea;padding:12px;margin-top:16px}
</style></head><body>
<h2>Création d'un compte agent</h2>
<form method="post">
 <label>Ministère
  <select name="ministere">
  {% for cle, m in ministeres.items() %}<option value="{{ cle }}">{{ m.nom }}</option>{% endfor %}
  </select></label>
 <label>Votre identifiant (administrateur du ministère)<input name="admin_user" required></label>
 <label>Votre mot de passe<input type="password" name="admin_password" required></label>
 <label>Identifiant du nouvel agent<input name="nouvel_agent" required></label>
 <label>Nom affiché (facultatif)<input name="nom_affiche"></label>
 <button type="submit">Créer le compte</button>
</form>
{% if resultat %}<div class="{{ 'ok' if resultat.ok else 'ko' }}">{{ resultat.msg }}</div>{% endif %}
</body></html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    resultat = traiter(request.form) if request.method == "POST" else None
    return render_template_string(PAGE, ministeres=MINISTERES, resultat=resultat)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
