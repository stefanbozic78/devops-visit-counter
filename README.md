# DevOps Visit Counter

[![CI](https://github.com/stefanbozic78/devops-visit-counter/actions/workflows/ci.yml/badge.svg)](https://github.com/stefanbozic78/devops-visit-counter/actions/workflows/ci.yml)

Mala Flask aplikacija koja broji posete i čuva brojač u Redis-u. Aplikacija je namerno jednostavna: poenta projekta je sve oko nje, odnosno Git, Docker, Docker Compose, Bash skripta i CI pipeline u GitHub Actions.

## Arhitektura

```text
          korisnik / curl
                 |
                 | HTTP :8080  (jedini port izložen ka hostu)
                 v
        +-------------------+
        |  app (Flask)      |
        +-------------------+
                 |
                 | Redis protokol, redis:6379 (samo interna Compose mreža)
                 v
        +-------------------+
        |  redis (Redis 7)  |
        +-------------------+
                 |
                 v
        +-------------------+
        |  volume redis_data|  (montiran na /data)
        +-------------------+
```

## Brzi start

Potrebno: Git, Docker i Docker Compose. Python ne mora da bude instaliran lokalno.

```bash
git clone https://github.com/stefanbozic78/devops-visit-counter.git
cd devops-visit-counter
cp .env.example .env
docker compose up -d --build
docker compose ps        # oba servisa treba da budu "healthy"
```

Provera:

```bash
curl http://localhost:8080/          # {"host":"<id kontejnera>","message":"Hello DevOps"}
curl http://localhost:8080/visits    # {"visits":1}           Napomena: visits ne mora da pocne od 1
curl http://localhost:8080/visits    # {"visits":2}
curl http://localhost:8080/health    # {"status":"ok"}
```

Zaustavljanje:

```bash
docker compose down        # volume ostaje, brojač se čuva
docker compose down -v     # briše i volume, brojač se gubi
```

Projekat sam pravio na Ubuntu-u preko WSL2 na Windows-u.

## Endpointi

| Metod | Putanja | Ponašanje |
|---|---|---|
| GET | `/` | Poruka i ime hosta (ID kontejnera) |
| GET | `/visits` | Uvećava brojač u Redis-u za 1 i vraća novu vrednost |
| GET | `/health` | `200 {"status":"ok"}` ako je Redis dostupan, inače `503 {"status":"error"}` |

Aplikacija svaki zahtev loguje na stdout (`docker compose logs app`).

## Konfiguracija

Sve se čita iz promenljivih okruženja. `.env` je u `.gitignore`, a u repozitorijumu je samo `.env.example`.

| Promenljiva | Podrazumevano | Značenje |
|---|---|---|
| `APP_PORT` | `8080` | Port na kom aplikacija sluša i koji je izložen ka hostu |
| `REDIS_HOST` | `redis` | Ime Redis servisa (Compose ga postavlja na `redis`) |
| `REDIS_PORT` | `6379` | Port na koji se aplikacija povezuje. Redis kontejner uvek sluša na 6379, pa ovu vrednost ne treba menjati bez izmene Redis konfiguracije. |

## Perzistencija brojača

Redis se pokreće sa `--appendonly yes` (AOF), što znači da se svaka izmena upisuje u log na disku. Folder `/data` u Redis kontejneru je montiran na imenovani volume `redis_data`, pa podaci žive nezavisno od kontejnera.

Provera:

```bash
curl http://localhost:8080/visits     # npr. {"visits":2}
docker compose down && docker compose up -d
curl http://localhost:8080/visits     # {"visits":3}, brojač se nastavlja
```

## Bash healthcheck skripta

```bash
./scripts/healthcheck.sh http://localhost:8080
```

Skripta poziva `/health` do 5 puta sa pauzom od 3 sekunde, svaki pokušaj loguje sa vremenom i HTTP statusom, i izlazi sa kodom `0` ako je aplikacija zdrava, odnosno `1` ako nije ni posle 5 pokušaja. Bez argumenta ispisuje uputstvo i izlazi sa kodom `1`.

Primer izlaza:

```text
[2026-11-10 10:32:01] Attempt 1/5 - HTTP 503
[2026-11-10 10:32:04] Attempt 2/5 - HTTP 200
Application is healthy
```

## Testovi i linter

```bash
python -m pip install -r requirements.txt
python -m pytest -v
ruff check app.py tests/
```

Koristim `python -m pytest` (a ne samo `pytest`) jer tako trenutni folder ulazi u Python putanju i test može da uveze `app.py`.

Trenutno postoji jedan test: proverava da `/` vraća HTTP 200, očekivanu poruku i neprazno ime hosta. `/visits` i `/health` još nisu pokriveni automatskim testovima, a proveravao sam ih ručno kroz `curl` i `docker compose`.

## CI pipeline

Workflow `.github/workflows/ci.yml` se pokreće na push na `main` i `feature/app-endpoints`, kao i na pull request ka `main`. Koraci, redom:

1. checkout koda,
2. podešavanje Python 3.14,
3. instalacija zavisnosti,
4. Ruff (linter),
5. Pytest,
6. build Docker slike.

Ako bilo koji korak padne, pipeline pada.

## Git tok rada

Istoriju sam gradio u malim commit-ovima. Funkcionalnost je razvijena na grani `feature/app-endpoints` i spojena u `main` kroz Pull Request (vidi karticu *Pull requests* u repozitorijumu).

## Zašto sam ovako odlučio

- **`python:3.14-slim`:** mnogo manja od pune Python slike, a za razliku od `alpine` koristi glibc, pa se pip paketi instaliraju bez kompajliranja. Verzija je navedena, nema `latest`.
- **Redosled u Dockerfile-u:** prvo se kopira `requirements.txt` i instaliraju zavisnosti, tek onda `app.py`. Dok se menja samo kod, Docker preskače sporu instalaciju zavisnosti (layer cache).
- **Korisnik `appuser`:** aplikacija ne radi kao root, pa bi eventualni proboj imao manje prava u kontejneru.
- **`REDIS_HOST=redis`, a ne `localhost`:** svaki kontejner ima svoj mrežni prostor, pa bi `localhost` u Flask kontejneru pokazivao na sam Flask kontejner. Compose mreža omogućava da se servisi nađu po imenu.
- **Healthcheck-ovi i `depends_on: service_healthy`:** Redis se proverava sa `redis-cli ping`, a Flask sa pozivom `/health` (Python `urllib`, jer `python:slim` nema `curl`). Aplikacija se pokreće tek kad je Redis spreman.
- **`restart: unless-stopped`:** oba servisa se sama podižu posle pada ili restarta Docker-a, osim ako ih ručno zaustavim.
- **Volume + AOF:** podaci ne zavise od životnog ciklusa kontejnera, a AOF smanjuje rizik od gubitka poslednjih izmena.
- **`INCR` u Redis-u:** uvećanje je atomično, pa istovremeni zahtevi ne mogu da pregaze jedan drugog (za razliku od „pročitaj pa upiši").
- **Redis bez lozinke:** odluka je svesna jer Redis nije izložen ka hostu, vidljiv je samo u internoj Compose mreži. Da je izložen, lozinka bi bila obavezna.

## Problemi na koje sam naišao

- **Docker u WSL-u:** `docker` komande su davale `permission denied` na Unix socket-u. Rešenje: dodavanje korisnika u `docker` grupu (`sudo usermod -aG docker $USER`) i restart WSL-a.
- **Flask ne vidi Redis:** u kontejneru je `localhost` bio pogrešna adresa za Redis. Rešenje: oba servisa su u istoj Compose mreži, a aplikacija koristi `REDIS_HOST=redis`.
- **Pogrešno mesto healthcheck-a:** Flask HTTP healthcheck sam greškom stavio pod `redis` servis u `compose.yaml`, pa je Redis stalno bio `unhealthy`. Razdvojio sam ih: `redis-cli ping` za Redis, HTTP `/health` za Flask.
- **Skripta bez prava izvršavanja:** zbog `core.fileMode=false` Git nije pamtio executable bit, pa je `healthcheck.sh` ušao u repozitorijum kao običan fajl. Rešio sam sa `git update-index --chmod=+x scripts/healthcheck.sh`.
- **Ruff i importi:** linter je javio pogrešan redosled importa, pa sam ih preuredio.

## Šta bih unapredio da imam više vremena

- **Gunicorn umesto Flask razvojnog servera.** Trenutno kontejner pokreće `python app.py`, odnosno Flask-ov ugrađeni server, koji nije namenjen produkciji.
- **Timeout-i za Redis** (`socket_connect_timeout`, `socket_timeout`), da `/health` vrati 503 umesto da čeka ako Redis ne odgovara.
- **Više testova** za `/visits` i `/health`, uključujući slučaj kada je Redis nedostupan (sa mock-ovanim Redis klijentom).
- **Odvojen `requirements-dev.txt`**, da pytest i ruff ne ulaze u produkcionu sliku.
- Za dalje: multi-stage build, Trivy skeniranje, objavljivanje slike u GitHub Container Registry i Kubernetes manifesti.

## Korišćeni AI alati

- **ChatGPT:** objašnjavanje koncepata (Git, Docker, Compose, Bash, pytest, GitHub Actions) i pomoć pri otklanjanju grešaka u konfiguraciji.
- **Claude:** pregled gotovog repozitorijuma i pomoć pri pisanju ovog README-a.

Rešenje sam razvijao i proveravao postepeno: ručno sam testirao ponašanje aplikacije, rad kontejnera, izlazne kodove skripte i rezultate CI-a.
