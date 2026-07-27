# rentalready-cli

Lire le contenu **propriétaire (host space)** de RentalReady depuis le terminal —
détails du logement, indicateurs du mois, et le détail financier des
réservations — en agissant comme le propriétaire connecté sur
`pms.rentalready.io`.

## Pourquoi ça réutilise la session du navigateur

L'espace propriétaire de RentalReady est une **appli Django rendue côté
serveur**, protégée par une **connexion à deux facteurs**. Il n'y a **pas d'API
JSON côté propriétaire** : les endpoints DRF `/api/v1/` et `/api/v2/` existent
mais sont **réservés au gestionnaire** — en tant que propriétaire ils renvoient
`403 « Vous n'êtes pas autorisé »`. La seule surface propriétaire est donc le
HTML du « host space » (`/authentification/host_*`, `/host_space/*`).

Plutôt que de réimplémenter le tunnel de connexion 2FA, la CLI s'authentifie
comme le navigateur du propriétaire — avec le cookie de session Django
**`sessionid`**, lu directement depuis un navigateur Chromium connecté (Chrome,
Arc, Brave, Edge) en déchiffrant son magasin de cookies avec la **clé du
trousseau macOS** (comme `notion-cli`). Rien à coller ; tu ne te reconnectes
dans le navigateur que quand la session expire (~14 jours).

## Utilisation

```bash
bin/rr login          # détecte une session navigateur connectée et la stocke
bin/rr doctor         # diagnostique la résolution de session
bin/rr overview       # indicateurs du mois (occupation, revenus nets, TJM, invité en cours)
bin/rr reservations --from 2026-07-01 --to 2026-07-31        # détail financier + totaux
bin/rr reservations --platform booking --json                # filtre plateforme, sortie JSON
bin/rr property       # fiche logement (adresse, wifi, codes, parking…)
bin/rr profile        # profil propriétaire (IBAN/BIC/tél/naissance masqués)
bin/rr profile --reveal
bin/rr whoami
bin/rr get /authentification/host_calendars/ --text          # échappatoire générique
```

Chaque commande de lecture accepte `--json`. `$RENTALREADY_SESSIONID` surcharge
tout. La session est stockée en chmod-600 dans
`~/.config/rentalready-cli/config.json`.

## Authentification

- **`bin/rr login`** — extraction automatique depuis Chrome/Arc/Brave/Edge, la
  première session valide gagne.
- **`bin/rr auth [--sessionid <valeur>]`** — coller le cookie `sessionid`
  (devtools → Application → Cookies → `pms.rentalready.io` → `sessionid`).
- Un renvoi vers `/account/login/` = session expirée → reconnecte-toi sur
  `pms.rentalready.io` puis relance `bin/rr login`.

## ⚠️ Données sensibles

`bin/rr profile` expose l'IBAN, le BIC, le téléphone et la date de naissance :
ils sont **masqués par défaut**, `--reveal` les affiche en clair.

## Ce qui n'est pas typé

Le **calendrier**, les **statistiques** (graphiques Highcharts) et les **avis**
sont rendus côté client : accessibles via `bin/rr get <path> --text`.

## Tests

```bash
uv run --with pytest --with click --with requests --with beautifulsoup4 \
  --with lxml --with pycryptodome python -m pytest tests/ -q
```
