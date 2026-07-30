# Installation

## Requirements

- Python 3.11+
- Git
- (Recommended) A dedicated lab environment or isolated VM — see
  [Responsible Use](../README.md#-responsible-use)

## Option 1 — Kali Linux (Recommended)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Option 2 — Docker

```bash
git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter

docker build -t oracle-hunter -f docker/Dockerfile .
docker run -it --rm -v $(pwd)/missions:/app/missions oracle-hunter
```

## Option 3 — Manual (any Linux/macOS)

```bash
git clone https://github.com/Panda1847/oracle-penetration-hunter.git
cd oracle-penetration-hunter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m oracle.core.setup
```

## Verifying Installation

```bash
oracle --version
oracle doctor   # checks dependencies and environment health
```

`The main entry point is `oracle`. Use `oracle --doctor` to verify your environment.
your real implementation before publishing — this doc currently describes the
intended UX scaffold.]`

## Next Steps

Continue to [QUICKSTART.md](QUICKSTART.md) to run your first mission.
