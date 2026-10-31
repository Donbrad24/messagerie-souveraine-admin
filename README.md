# Messagerie souveraine de l'administration - équipe AgroSmart

Sprint technique pré-hackathon 2026 (Hackathon 226, MTDPCE - DGTD) - challenge « La messagerie souveraine de l'administration ».

## Concept

Une messagerie instantanée pour les agents publics, hébergée sur une infrastructure maîtrisée, avec chiffrement de bout en bout. Les agents sont organisés par **ministère** : chaque ministère a son espace, ses salons, et ses propres administrateurs, qui créent les comptes de leurs agents sans être administrateurs du serveur.

## Architecture

    Navigateur (agent)  ->  Element Web (8080)  ->  Synapse (8008)  ->  PostgreSQL
    Administrateur de ministère  ->  Portail de comptes (5000)  ->  API d'administration de Synapse

Trois conteneurs de base (Synapse, Element, PostgreSQL) plus un portail Flask. Aucun service tiers, aucune API externe. Le serveur est isolé : pas de fédération.

## Technologies et licences

| Technologie | Rôle | Licence |
|---|---|---|
| Synapse (github.com/element-hq/synapse) | Serveur Matrix | AGPL-3.0 |
| Element Web (github.com/element-hq/element-web) | Client web | AGPL-3.0 ou GPL-3.0 |
| PostgreSQL (postgresql.org) | Base de données | PostgreSQL License |
| Flask (github.com/pallets/flask) | Portail de comptes | BSD-3-Clause |
| Requests (github.com/psf/requests) | Appels au serveur depuis le portail | Apache-2.0 |
| Docker et Docker Compose (github.com/docker) | Déploiement | Apache-2.0 |
| Code de ce dépôt (portail, scripts, configuration) | - | Apache-2.0 (fichier LICENSE) |

## Niveau d'engagement open source : Étendre et adapter

Nous partons de Synapse et d'Element, sans modifier leur code : nous les configurons selon le socle de sécurité et nous ajoutons notre propre portail de gestion des comptes par ministère, ainsi que le script de révocation.

## Socle de sécurité

- **Chiffrement de bout en bout** : protocole Matrix (Olm/Megolm), activé par défaut dans tous les salons. Aucune cryptographie développée par l'équipe.
- **Hébergement souverain** : installation en une commande (`./install.sh`), sans service tiers.
- **Identité vérifiée** : inscription fermée ; seuls les comptes créés par un administrateur existent.
- **Révocation immédiate** : `revoquer.sh` désactive le compte et invalide tous ses appareils.
- **Minimisation des métadonnées** : pas de fédération, présence désactivée, recherche d'utilisateurs limitée aux salons partagés.

## Fonctionnalité innovante : ministères et administrateurs délégués

- Un **espace par ministère**, avec des salons ouverts à tous les membres du ministère (« Courrier officiel ») et des salons **sur invitation uniquement** (« Direction »).
- Trois rôles : super administrateur (`admin`), administrateur de ministère (niveau 100 dans son espace seulement), agent.
- Le **portail** (http://localhost:5000) permet à un administrateur de ministère de créer des comptes dans **son** ministère uniquement. Le serveur vérifie son niveau dans l'espace ; le jeton du super administrateur ne quitte jamais le serveur. Chaque action est journalisée.

## Installation

Prérequis : Docker et Docker Compose, ports 8008, 8080 et 5000 libres.

    git clone https://github.com/Donbrad24/messagerie-souveraine-admin.git
    cd messagerie-souveraine-admin
    ./install.sh

La messagerie est alors disponible sur http://localhost:8080.

### Comptes de démonstration (fictifs)

| Compte | Mot de passe | Rôle |
|---|---|---|
| admin | Demo-Admin-2026! | Super administrateur |
| admin.sante / admin.education / admin.finances | Demo-AdmSante-2026! / Demo-AdmEduc-2026! / Demo-AdmFin-2026! | Administrateurs de ministère |
| agent.sante / agent.education / agent.finances | Demo-Sante-2026! / Demo-Educ-2026! / Demo-Fin-2026! | Agents |
| agent.comptable | Demo-Compta-2026! | Agent (test d'accès) |

### Activer les ministères et le portail

1. Connecté en `admin`, créer un espace privé par ministère et inviter `admin.<ministère>` ; le promouvoir **Administrateur** (Paramètres de l'espace, Rôles et permissions).
2. Pour les salons sensibles : Paramètres du salon, Sécurité et confidentialité, Accès : **Privé (sur invitation uniquement)**.
3. Copier l'identifiant de chaque espace (Paramètres de l'espace, Avancé), puis :

        cp portail/ministeres.example.json portail/ministeres.json   # y coller les identifiants
        cp .env.example .env                                          # y mettre le mot de passe de admin
        docker compose up -d --build portail

## Démonstrations de sécurité

- **Le serveur ne lit rien** : après un message, `docker compose exec db psql -U synapse -d synapse -c "SELECT count(*) FROM event_json WHERE json LIKE '%MOT-ENVOYE%';"` renvoie 0 ; les événements sont de type `m.room.encrypted`.
- **Intrus** : l'inscription est refusée (`M_FORBIDDEN`) et un compte inexistant ne peut pas se connecter.
- **Révocation** : `ADMIN_TOKEN=<jeton> ./revoquer.sh agent.comptable`.

## Limites connues

- **Pas de second facteur** : l'authentification se fait par mot de passe seul. Piste : brancher Keycloak ou Authentik.
- Démonstration en **HTTP local** ; la production demande HTTPS et un nom de domaine.
- Les mots de passe temporaires créés par le portail ne sont pas à changer obligatoirement à la première connexion.
- Le super administrateur voit la liste des salons et peut les rejoindre, mais ne lit pas l'historique chiffré.
- Les métadonnées (qui parle à qui, quand) restent visibles du serveur.
- La création des espaces ministériels est manuelle ; le serveur web de développement Flask suffit pour la démonstration, pas pour la production.
- Le mot de passe de PostgreSQL (`changeme`) est celui de la démonstration.
