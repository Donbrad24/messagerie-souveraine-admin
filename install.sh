#!/bin/bash
# Installation de la messagerie souveraine (équipe AgroSmart) en une commande.
set -e
cd "$(dirname "$0")"

if [ -f synapse-data/homeserver.yaml ]; then
  echo "Déjà installé. Pour démarrer : docker compose up -d db synapse element"
  exit 0
fi

echo "1/4 Génération de la configuration de Synapse..."
docker compose run --rm -T -e SYNAPSE_SERVER_NAME=localhost -e SYNAPSE_REPORT_STATS=no synapse generate

echo "2/4 Application des réglages de sécurité..."
docker compose run --rm -T --entrypoint python synapse - << 'PY'
import re
chemin = "/data/homeserver.yaml"
texte = open(chemin).read()
base = """database:
  name: psycopg2
  args:
    user: synapse
    password: changeme
    database: synapse
    host: db
    cp_min: 5
    cp_max: 10
"""
texte, n = re.subn(r"database:\n  name: sqlite3\n  args:\n    database: [^\n]*\n", base, texte)
if n != 1:
    raise SystemExit("Bloc database introuvable : vérifiez homeserver.yaml")
texte += """
enable_registration: false
encryption_enabled_by_default_for_room_type: all
presence:
  enabled: false
allow_guest_access: false
federation_domain_whitelist: []
"""
open(chemin, "w").write(texte)
PY

echo "3/4 Démarrage des services..."
docker compose up -d db synapse element
printf "Attente de Synapse"
for i in $(seq 1 60); do
  if curl -fs http://localhost:8008/health > /dev/null; then break; fi
  printf "."; sleep 2
done
echo
curl -fs http://localhost:8008/health > /dev/null || { echo "Synapse ne répond pas."; exit 1; }

echo "4/4 Création des comptes de démonstration (fictifs)..."
creer() {
  docker compose exec -T synapse register_new_matrix_user -c /data/homeserver.yaml -u "$1" -p "$2" $3 http://localhost:8008 > /dev/null
  echo "  compte $1 créé"
}
creer admin            'Demo-Admin-2026!'     -a
creer admin.sante      'Demo-AdmSante-2026!'  --no-admin
creer admin.education  'Demo-AdmEduc-2026!'   --no-admin
creer admin.finances   'Demo-AdmFin-2026!'    --no-admin
creer agent.sante      'Demo-Sante-2026!'     --no-admin
creer agent.education  'Demo-Educ-2026!'      --no-admin
creer agent.finances   'Demo-Fin-2026!'       --no-admin
creer agent.comptable  'Demo-Compta-2026!'    --no-admin

echo
echo "Installation terminée. Messagerie : http://localhost:8080"
