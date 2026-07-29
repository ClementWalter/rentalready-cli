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
rr login          # détecte une session navigateur connectée et la stocke
rr doctor         # diagnostique la résolution de session
rr overview       # indicateurs du mois (occupation, revenus nets, TJM, invité en cours)
rr reservations --from 2026-07-01 --to 2026-07-31        # détail financier + totaux
rr reservations --platform booking --json                # filtre plateforme, sortie JSON
rr projection     # projection de revenus annuels (saison récente par mois)
rr projection --fill                                     # extrapole un mois pic sous-réservé
rr property       # fiche logement (adresse, wifi, codes, parking…)
rr profile        # profil propriétaire (IBAN/BIC/tél/naissance masqués)
rr profile --reveal
rr whoami
rr get /authentification/host_calendars/ --text          # échappatoire générique
```

Chaque commande de lecture accepte `--json`. `$RENTALREADY_SESSIONID` surcharge
tout. La session est stockée en chmod-600 dans
`~/.config/rentalready-cli/config.json`.

## Authentification

- **`rr login`** — extraction automatique depuis Chrome/Arc/Brave/Edge, la
  première session valide gagne.
- **`rr auth [--sessionid <valeur>]`** — coller le cookie `sessionid`
  (devtools → Application → Cookies → `pms.rentalready.io` → `sessionid`).
- Un renvoi vers `/account/login/` = session expirée → reconnecte-toi sur
  `pms.rentalready.io` puis relance `rr login`.

## Cache

Le contenu propriétaire change peu et le portail est lent (~4 s/requête), donc
`overview`, `property` et `reservations` mettent en cache leurs réponses sur
disque (`~/.cache/rentalready-cli/`, TTL 6 h — surchargeable par `$RR_CACHE_TTL`
en secondes). Un `reservations` sur un an passe de ~30 s à ~0,2 s. `--refresh`
force le rafraîchissement. `profile`/`whoami` ne sont **jamais** mis en cache
(IBAN/BIC/date de naissance).

## ⚠️ Données sensibles

`rr profile` expose l'IBAN, le BIC, le téléphone et la date de naissance :
ils sont **masqués par défaut**, `--reveal` les affiche en clair.

## Ce qui n'est pas typé

Le **calendrier**, les **statistiques** (graphiques Highcharts) et les **avis**
sont rendus côté client : accessibles via `rr get <path> --text`.

## Tests

```bash
uv run --with pytest --with click --with requests --with beautifulsoup4 \
  --with lxml --with pycryptodome python -m pytest tests/ -q
```
