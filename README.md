# rentalready-cli

**Visibility: public.**

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
rr monthly        # revenus nets par mois : une ligne par mois, une colonne par année
rr monthly --nights                                      # + nuits réservées
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
- Sans session stockée, chaque commande cherche elle-même une session
  navigateur ; si la session stockée renvoie vers `/account/login/`, elle
  réessaie une fois avec une session navigateur plus récente. Sinon la session
  a expiré partout → reconnecte-toi sur `pms.rentalready.io`, puis réessaie.
- Seuls les navigateurs dont le magasin de cookies contient une session
  RentalReady demandent leur clé au trousseau macOS.

## Extension Claude Desktop

`mcpb.json` personnalise l'extension que construit
`mcp-bridge pack rentalready-cli`, installable d'un double-clic sans terminal :
se connecter au portail propriétaire dans Chrome, puis cliquer « Toujours
autoriser » quand macOS demande l'accès au trousseau.

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
uv run --script tests/test_rr.py
uv run --script tests/test_auth_contract.py
```

## Privacy Policy

The Claude Desktop extension built from this repository keeps your data on your
Mac and talks only to the service it connects to. Full policy:
<https://clementwalter.github.io/claude-extensions/privacy/>
