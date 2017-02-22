from pathlib import Path

HOME = Path.home()
USER = ''
HOSTNAME = ''
PORT = 22
KNOWN_HOSTS = HOME / ".ssh" / "known_hosts"
CONFIG_PATH = Path(__file__).with_name('config.py')