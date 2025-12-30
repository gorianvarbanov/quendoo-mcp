"""API Key Manager - Set, get, and cleanup API keys with 24h cache"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

API_KEY_CACHE_FILE = Path.home() / ".quendoo_api_key_cache.json"


def set_api_key(api_key: str) -> dict:
    """
    Set Quendoo API key and cache it for 24 hours.

    Args:
        api_key: The Quendoo API key to set

    Returns:
        dict with success status and expiry time
    """
    expiry = datetime.now() + timedelta(hours=24)

    cache_data = {
        "api_key": api_key,
        "set_at": datetime.now().isoformat(),
        "expires_at": expiry.isoformat()
    }

    # Write to cache file
    with open(API_KEY_CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=2)

    # Also update .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update or add QUENDOO_API_KEY line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('QUENDOO_API_KEY='):
                lines[i] = f'QUENDOO_API_KEY={api_key}\n'
                updated = True
                break

        if not updated:
            # Find the API Keys section
            for i, line in enumerate(lines):
                if '# API Keys' in line:
                    lines.insert(i + 1, f'QUENDOO_API_KEY={api_key}\n')
                    updated = True
                    break

            if not updated:
                lines.append(f'\nQUENDOO_API_KEY={api_key}\n')

        with open(env_file, 'w') as f:
            f.writelines(lines)

    return {
        "success": True,
        "message": f"API key set successfully. Expires at {expiry.strftime('%Y-%m-%d %H:%M:%S')}",
        "expires_at": expiry.isoformat(),
        "cached_location": str(API_KEY_CACHE_FILE),
        "env_file_updated": env_file.exists()
    }


def get_api_key() -> str | None:
    """
    Get cached API key if not expired.

    Returns:
        The API key if valid and not expired, None otherwise
    """
    if not API_KEY_CACHE_FILE.exists():
        # Try to get from environment
        return os.getenv("QUENDOO_API_KEY")

    try:
        with open(API_KEY_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)

        expires_at = datetime.fromisoformat(cache_data["expires_at"])

        # Check if expired
        if datetime.now() > expires_at:
            print(f"[API Key Manager] Cached key expired at {expires_at}")
            return None

        return cache_data["api_key"]
    except Exception as e:
        print(f"[API Key Manager] Error reading cache: {e}")
        return os.getenv("QUENDOO_API_KEY")


def cleanup_api_key() -> dict:
    """
    Remove cached API key and clear from .env file.

    Returns:
        dict with success status
    """
    removed_files = []

    # Remove cache file
    if API_KEY_CACHE_FILE.exists():
        API_KEY_CACHE_FILE.unlink()
        removed_files.append(str(API_KEY_CACHE_FILE))

    # Clear from .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Remove or comment out QUENDOO_API_KEY line
        new_lines = []
        for line in lines:
            if line.startswith('QUENDOO_API_KEY='):
                new_lines.append(f'# {line}')  # Comment it out
            else:
                new_lines.append(line)

        with open(env_file, 'w') as f:
            f.writelines(new_lines)

        removed_files.append(str(env_file))

    return {
        "success": True,
        "message": "API key cleaned up successfully",
        "files_updated": removed_files
    }


def get_api_key_status() -> dict:
    """
    Get status of cached API key.

    Returns:
        dict with cache status, expiry, and whether key is valid
    """
    if not API_KEY_CACHE_FILE.exists():
        return {
            "cached": False,
            "valid": False,
            "message": "No cached API key found",
            "env_fallback": bool(os.getenv("QUENDOO_API_KEY"))
        }

    try:
        with open(API_KEY_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)

        set_at = datetime.fromisoformat(cache_data["set_at"])
        expires_at = datetime.fromisoformat(cache_data["expires_at"])
        now = datetime.now()

        is_valid = now < expires_at
        time_remaining = expires_at - now

        return {
            "cached": True,
            "valid": is_valid,
            "set_at": set_at.strftime('%Y-%m-%d %H:%M:%S'),
            "expires_at": expires_at.strftime('%Y-%m-%d %H:%M:%S'),
            "time_remaining_hours": time_remaining.total_seconds() / 3600 if is_valid else 0,
            "api_key_preview": cache_data["api_key"][:10] + "..." if is_valid else None
        }
    except Exception as e:
        return {
            "cached": True,
            "valid": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python api_key_manager.py set <api_key>")
        print("  python api_key_manager.py get")
        print("  python api_key_manager.py status")
        print("  python api_key_manager.py cleanup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "set":
        if len(sys.argv) < 3:
            print("Error: API key required")
            sys.exit(1)
        result = set_api_key(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif command == "get":
        api_key = get_api_key()
        if api_key:
            print(f"API Key: {api_key[:10]}...")
        else:
            print("No valid API key found")

    elif command == "status":
        status = get_api_key_status()
        print(json.dumps(status, indent=2))

    elif command == "cleanup":
        result = cleanup_api_key()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
