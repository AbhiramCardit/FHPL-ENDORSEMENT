#!/usr/bin/env python3
"""
FHPL Endorsement Automation — Docker Management Tool

Single entry point for managing the entire Docker Compose stack.
Usage: python manage.py <command> [options]
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import List, Optional


# ═══════════════════════════════════════════════════════════
#  Logging Setup
# ═══════════════════════════════════════════════════════════

class ColorFormatter(logging.Formatter):
    """Console formatter with ANSI colors and level symbols."""

    COLORS = {
        "INFO": "\033[96m",        # Cyan
        "SUCCESS": "\033[92m",     # Green
        "WARNING": "\033[93m",     # Yellow
        "ERROR": "\033[91m",       # Red
        "CRITICAL": "\033[91m\033[1m",  # Bold Red
        "DEBUG": "\033[94m",       # Blue
        "HEADER": "\033[95m",      # Magenta
        "BOLD": "\033[1m",
        "RESET": "\033[0m",
    }

    SYMBOLS = {
        "INFO": "→",
        "SUCCESS": "✓",
        "WARNING": "⚠",
        "ERROR": "✗",
        "CRITICAL": "☠",
        "DEBUG": "•",
        "STEP": "▶",
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.platform != "win32"

    def _colorize(self, text: str, color_name: str) -> str:
        if not self.use_colors:
            return text
        color = self.COLORS.get(color_name, "")
        return f"{color}{text}{self.COLORS['RESET']}" if color else text

    def format(self, record: logging.LogRecord) -> str:
        msg = str(record.msg)

        # Detect custom markers in the message
        if "[SUCCESS]" in msg:
            symbol, color = self.SYMBOLS["SUCCESS"], "SUCCESS"
        elif "[WARNING]" in msg:
            symbol, color = self.SYMBOLS["WARNING"], "WARNING"
        elif "[ERROR]" in msg:
            symbol, color = self.SYMBOLS["ERROR"], "ERROR"
        elif "[STEP]" in msg:
            symbol, color = self.SYMBOLS["STEP"], "INFO"
        else:
            symbol, color = self.SYMBOLS.get(record.levelname, ""), record.levelname

        # Prepend symbol (skip headers / indented lines)
        if symbol and not msg.startswith(("===", " ")):
            record.msg = f"{symbol} {msg}"

        # Apply colour
        if self.use_colors:
            if msg.startswith("==="):
                record.msg = self._colorize(str(record.msg), "HEADER")
            else:
                record.msg = self._colorize(str(record.msg), color)

        return super().format(record)


# --- Bootstrap logger --------------------------------------------------------
_log_dir = "logs"
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, f"manage-{datetime.now():%Y%m%d}.log")

_file_handler = logging.FileHandler(_log_file, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(ColorFormatter())

logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _console_handler])
logger = logging.getLogger("manage")


# ═══════════════════════════════════════════════════════════
#  Docker Manager
# ═══════════════════════════════════════════════════════════

class DockerManager:
    """Manages the full Docker Compose lifecycle for the endorsement platform."""

    VOLUME_NAMES = [
        "endorsements_postgres_data",
        "endorsements_redis_data",
        "endorsements_minio_data",
    ]

    # Services that have health-checks we can probe over HTTP
    HEALTH_ENDPOINTS = {
        "backend": "http://localhost:8000/health",
        "frontend": "http://localhost:5173",
    }

    def __init__(self, dev_mode: bool = False):
        self.dev_mode = dev_mode
        self.compose_file = "docker-compose.dev.yml" if dev_mode else "docker-compose.yml"
        self.env_label = "Development" if dev_mode else "Production"

    # ─── Helpers ──────────────────────────────────────────
    def _compose_cmd(self) -> List[str]:
        if self.dev_mode:
            return ["docker", "compose", "-f", self.compose_file]
        return ["docker", "compose"]

    def _run(self, cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
        logger.info(f"[STEP] Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, check=check, text=True, capture_output=True)
            if result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        logger.info(f"  {line.strip()}")
            if result.stderr and "already exists" not in result.stderr.lower():
                for line in result.stderr.strip().splitlines():
                    if line.strip():
                        logger.warning(f"  {line.strip()}")
            return result
        except subprocess.CalledProcessError as exc:
            logger.error(f"Command failed (exit {exc.returncode})")
            if exc.stderr:
                logger.error(f"  {exc.stderr.strip()}")
            raise

    def _wait(self, seconds: int = 10) -> None:
        logger.info(f"[STEP] Waiting {seconds}s for services to initialise…")
        time.sleep(seconds)
        logger.info("[SUCCESS] Wait complete")

    def _probe_http(self, name: str, url: str, timeout: int = 30) -> None:
        """Poll an HTTP endpoint until it responds or times out."""
        import urllib.request

        logger.info(f"[STEP] Probing {name} at {url}…")
        deadline = time.time() + timeout
        while True:
            try:
                urllib.request.urlopen(url, timeout=5)
                logger.info(f"[SUCCESS] {name} is reachable!")
                return
            except Exception:
                pass
            if time.time() > deadline:
                logger.warning(f"[WARNING] {name} health-check timed out after {timeout}s")
                return
            time.sleep(2)

    # ─── Volume Management ────────────────────────────────
    def ensure_volumes(self) -> None:
        logger.info(f"\n=== {self.env_label} Volume Check ===")
        existing = self._run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"]
        ).stdout.splitlines()

        for vol in self.VOLUME_NAMES:
            if vol not in existing:
                logger.info(f"[STEP] Creating volume: {vol}")
                self._run(["docker", "volume", "create", vol])
            else:
                logger.debug(f"Volume exists: {vol}")

    # ─── Core Commands ────────────────────────────────────
    def up(self, build: bool = False) -> None:
        """Start all containers."""
        logger.info(f"\n=== Starting {self.env_label} Services ===")
        self.ensure_volumes()

        cmd = self._compose_cmd() + ["up", "-d"]
        if build:
            cmd.append("--build")
            logger.info(f"[STEP] Building and starting {self.env_label.lower()} containers…")
        else:
            logger.info(f"[STEP] Starting {self.env_label.lower()} containers…")

        self._run(cmd)
        self._wait(15)

        # Probe health endpoints
        for name, url in self.HEALTH_ENDPOINTS.items():
            self._probe_http(name, url)

        logger.info(f"\n[SUCCESS] All {self.env_label.lower()} services are up!")
        self.urls()

        logger.info("\n=== Persistent Volumes ===")
        for vol in self.VOLUME_NAMES:
            logger.info(f"  • {vol}")

    def down(self, volumes: bool = False) -> None:
        """Stop all containers. Optionally remove volumes."""
        logger.info(f"\n=== Stopping {self.env_label} Services ===")

        if volumes:
            logger.warning("\n[WARNING] ⚠ ⚠ ⚠  DANGER ZONE  ⚠ ⚠ ⚠")
            logger.warning("This will permanently delete ALL data (Postgres, Redis, MinIO)!")
            confirm = input("\nType 'yes' to confirm: ")
            if confirm.strip().lower() != "yes":
                logger.info("[SUCCESS] Operation cancelled")
                return
            logger.warning("[STEP] Removing containers and volumes…")
            cmd = self._compose_cmd() + ["down", "-v"]
        else:
            logger.info("[STEP] Stopping containers (data volumes preserved)…")
            cmd = self._compose_cmd() + ["down"]

        self._run(cmd)

        if volumes:
            logger.warning("[SUCCESS] All services and data volumes removed!")
        else:
            logger.info("[SUCCESS] Services stopped. Data volumes preserved.")

    def restart(self) -> None:
        """Restart all containers in-place."""
        logger.info(f"\n=== Restarting {self.env_label} Services ===")
        self._run(self._compose_cmd() + ["restart"])
        self._wait(15)
        logger.info(f"[SUCCESS] All {self.env_label.lower()} services restarted!")
        self.urls()

    def restart_full(self, build: bool = False) -> None:
        """Full restart — down then up."""
        logger.info(f"\n=== Full {self.env_label} Restart ===")
        self.down(volumes=False)
        self.up(build=build)
        logger.info("[SUCCESS] Full restart completed!")

    # ─── Logs ─────────────────────────────────────────────
    def logs(self, service: Optional[str] = None, tail: int = 100) -> None:
        """Stream service logs (Ctrl-C to stop)."""
        logger.info(f"\n=== {self.env_label} Service Logs ===")
        if service:
            logger.info(f"[STEP] Tailing logs for: {service}")
        else:
            logger.info("[STEP] Tailing logs for all services")

        cmd = self._compose_cmd() + ["logs", "--tail", str(tail), "-f"]
        if service:
            cmd.append(service)

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            logger.info("\n[SUCCESS] Stopped viewing logs")

    # ─── Status ───────────────────────────────────────────
    def status(self) -> None:
        """Show container and volume status."""
        logger.info(f"\n=== {self.env_label} Service Status ===")
        self._run(self._compose_cmd() + ["ps"], check=False)

        logger.info("\n=== Volume Status ===")
        self._run(
            ["docker", "volume", "ls", "--format", "table {{.Name}}\t{{.Driver}}"],
            check=False,
        )

    # ─── Database ─────────────────────────────────────────
    def init_db(self) -> None:
        """Run Alembic migrations inside the backend container."""
        logger.info("\n=== Database Initialisation ===")
        logger.info("[STEP] Running Alembic migrations…")
        self._run(
            self._compose_cmd() + ["exec", "backend", "alembic", "upgrade", "head"]
        )
        logger.info("[SUCCESS] Database migrations applied!")

    def seed(self) -> None:
        """Run the seed script inside the backend container."""
        logger.info("\n=== Seeding Database ===")
        logger.info("[STEP] Inserting development seed data…")
        self._run(
            self._compose_cmd()
            + ["exec", "backend", "python", "-m", "scripts.seed_users"]
        )
        logger.info("[SUCCESS] Seed data inserted!")

    # ─── Integration Tests ────────────────────────────────
    def test(self) -> None:
        """Quick smoke-test of running services."""
        import urllib.request

        logger.info(f"\n=== {self.env_label} Integration Test ===")

        # Backend /health
        try:
            logger.info("[STEP] Testing backend health…")
            resp = urllib.request.urlopen("http://localhost:8000/health", timeout=10)
            data = json.loads(resp.read().decode())
            logger.info(f"[SUCCESS] Backend: status={data.get('status')} env={data.get('env')}")
        except Exception as exc:
            logger.error(f"[ERROR] Backend health check failed: {exc}")

        # Frontend
        try:
            logger.info("[STEP] Testing frontend…")
            urllib.request.urlopen("http://localhost:5173", timeout=10)
            logger.info("[SUCCESS] Frontend is reachable")
        except Exception as exc:
            logger.error(f"[ERROR] Frontend check failed: {exc}")

        # MinIO
        try:
            logger.info("[STEP] Testing MinIO…")
            urllib.request.urlopen("http://localhost:9000/minio/health/live", timeout=10)
            logger.info("[SUCCESS] MinIO is reachable")
        except Exception as exc:
            logger.error(f"[ERROR] MinIO check failed: {exc}")

    # ─── URLs ─────────────────────────────────────────────
    def urls(self) -> None:
        """Print access URLs for every service."""
        logger.info(f"\n=== {self.env_label} Access URLs ===")
        logger.info("📱  Frontend:          http://localhost:5173")
        logger.info("🔧  Backend API:       http://localhost:8000")
        logger.info("📖  Swagger Docs:      http://localhost:8000/docs")
        logger.info("❤️   Health Check:      http://localhost:8000/health")
        logger.info("🗄️   MinIO Console:     http://localhost:9001")
        logger.info("🐘  PostgreSQL:        localhost:5432")
        logger.info("🔴  Redis:             localhost:6379")


# ═══════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════

USAGE = f"""
{ColorFormatter.COLORS['HEADER']}FHPL Endorsement Automation — Docker Management{ColorFormatter.COLORS['RESET']}
{'═' * 50}

{ColorFormatter.COLORS['BOLD']}Usage:{ColorFormatter.COLORS['RESET']} python manage.py <command> [options]

{ColorFormatter.COLORS['BOLD']}Commands:{ColorFormatter.COLORS['RESET']}
    {ColorFormatter.COLORS['INFO']}up{ColorFormatter.COLORS['RESET']}              Start containers (--build to rebuild)
    {ColorFormatter.COLORS['WARNING']}down{ColorFormatter.COLORS['RESET']}            Stop containers (--volumes to remove data)
    {ColorFormatter.COLORS['INFO']}restart{ColorFormatter.COLORS['RESET']}         Quick restart (in-place)
    {ColorFormatter.COLORS['INFO']}restart-full{ColorFormatter.COLORS['RESET']}    Full restart (down → up, --build to rebuild)
    {ColorFormatter.COLORS['INFO']}logs{ColorFormatter.COLORS['RESET']}            Stream logs (--service=NAME for one service)
    {ColorFormatter.COLORS['INFO']}status{ColorFormatter.COLORS['RESET']}          Show container & volume status
    {ColorFormatter.COLORS['INFO']}init-db{ColorFormatter.COLORS['RESET']}         Run Alembic migrations
    {ColorFormatter.COLORS['INFO']}seed{ColorFormatter.COLORS['RESET']}            Insert development seed data
    {ColorFormatter.COLORS['INFO']}test{ColorFormatter.COLORS['RESET']}            Smoke-test running services
    {ColorFormatter.COLORS['INFO']}urls{ColorFormatter.COLORS['RESET']}            Show access URLs

{ColorFormatter.COLORS['BOLD']}Options:{ColorFormatter.COLORS['RESET']}
    --dev           Use docker-compose.dev.yml
    --build         Rebuild images before starting
    --volumes       Remove data volumes on 'down' (⚠ destructive)
    --service=NAME  Target a specific service for 'logs'

{ColorFormatter.COLORS['BOLD']}Examples:{ColorFormatter.COLORS['RESET']}
    python manage.py up --build          # Build & start everything
    python manage.py logs --service=backend
    python manage.py init-db             # Run migrations
    python manage.py seed                # Seed dev users
    python manage.py down --volumes      # Nuke everything
"""


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    command = sys.argv[1]
    opts = sys.argv[2:]
    dev_mode = "--dev" in opts

    mgr = DockerManager(dev_mode=dev_mode)

    try:
        if command == "up":
            mgr.up(build="--build" in opts)
        elif command == "down":
            mgr.down(volumes="--volumes" in opts)
        elif command == "restart":
            mgr.restart()
        elif command == "restart-full":
            mgr.restart_full(build="--build" in opts)
        elif command == "logs":
            service = None
            for o in opts:
                if o.startswith("--service="):
                    service = o.split("=", 1)[1]
            mgr.logs(service=service)
        elif command == "status":
            mgr.status()
        elif command == "init-db":
            mgr.init_db()
        elif command == "seed":
            mgr.seed()
        elif command == "test":
            mgr.test()
        elif command == "urls":
            mgr.urls()
        else:
            logger.error(f"Unknown command: {command}")
            print(USAGE)
            sys.exit(1)
    except Exception as exc:
        logger.error(f"Operation failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
