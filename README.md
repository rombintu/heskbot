## HESK BOT

### Pre-install
```bash
docker run --network=host --name redis -d redis 
cp .env.example .env
vim .env # Change variables
poetry install
```
### Run
```bash
poetry run python3 main.py
```