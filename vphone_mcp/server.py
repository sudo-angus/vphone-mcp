"""vphone-mcp: MCP server for programmatic iOS VM control."""

import base64
import os
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .actions import (
    APP_SWITCHER,
    BACK_BUTTON,
    CONTROL_CENTER,
    NEXT_PAGE,
    NOTIFICATION_CENTER,
    PREV_PAGE,
    SCROLL_DOWN,
    SCROLL_UP,
    SEARCH_BAR,
    app_position,
)
from .client import VPhoneClient

mcp = FastMCP("vphone")

# ---------------------------------------------------------------------------
# Socket discovery
# ---------------------------------------------------------------------------

def _socket_path() -> str:
    """Resolve the vphone.sock path."""
    # Explicit env var takes priority
    if env := os.environ.get("VPHONE_SOCK"):
        return env
    # Default: look for vm/vphone.sock relative to common project locations
    candidates = [
        Path.home() / "localdev" / "experiments" / "vphone-cli" / "vm" / "vphone.sock",
        Path.cwd() / "vm" / "vphone.sock",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # Fall back to first candidate (will fail with clear error)
    return str(candidates[0])


def _client() -> VPhoneClient:
    return VPhoneClient(_socket_path())


def _require_ok(resp: dict) -> str:
    """Return success message or raise with error detail."""
    if resp.get("ok"):
        return resp.get("message") or resp.get("path") or "ok"
    raise RuntimeError(resp.get("error", "unknown error"))


# ---------------------------------------------------------------------------
# Layer 1: Hardware keys
# ---------------------------------------------------------------------------

@mcp.tool()
def go_home() -> str:
    """Press the home button to return to the home screen."""
    return _require_ok(_client().key("home"))


@mcp.tool()
def press_power() -> str:
    """Press the power button (lock/wake)."""
    return _require_ok(_client().key("power"))


@mcp.tool()
def volume_up() -> str:
    """Press volume up."""
    return _require_ok(_client().key("volup"))


@mcp.tool()
def volume_down() -> str:
    """Press volume down."""
    return _require_ok(_client().key("voldown"))


# ---------------------------------------------------------------------------
# Layer 2: Screenshots
# ---------------------------------------------------------------------------

@mcp.tool()
def screenshot(full_resolution: bool = False) -> str:
    """Take a screenshot of the VM display and save it to a temp file.

    Returns the file path. Use the Read tool to view the image.

    Prefer the default compact format for all routine work (reading UI text,
    locating tap targets, verifying navigation state). Only use
    full_resolution=True when you specifically need color accuracy
    (e.g. verifying theme colors, checking image assets).

    Tap coordinates use the full-resolution pixel space (1290x2796). If you
    identified a target in a compact screenshot (430x932), multiply the
    coordinates by 3 before calling tap().

    Args:
        full_resolution: If False (default), saves a compact grayscale JPEG
            (430x932, ~20-50KB) suitable for layout analysis and text recognition.
            If True, saves a full-resolution color PNG (1290x2796, 2-5MB).
    """
    if full_resolution:
        path = os.path.join(tempfile.gettempdir(), "vphone-mcp-screen.png")
        resp = _client().screenshot(path)
        _require_ok(resp)
        return path

    resp = _client().screenshot()
    _require_ok(resp)
    image_b64 = resp.get("image")
    if not image_b64:
        raise RuntimeError("no image data in response")
    path = os.path.join(tempfile.gettempdir(), "vphone-mcp-screen.jpg")
    Path(path).write_bytes(base64.b64decode(image_b64))
    return path


# ---------------------------------------------------------------------------
# Layer 3: Pre-mapped navigation
# ---------------------------------------------------------------------------

@mcp.tool()
def open_app(name: str) -> str:
    """Tap a preset system app icon on the default home screen.

    IMPORTANT: This only works for the 18 built-in apps listed below. For any
    third-party or user-installed app, use launch_app(bundle_id) instead — it
    can start any app by bundle identifier. Use list_apps() to discover
    installed apps and their bundle IDs.

    First presses home to ensure we're on the home screen, then taps the app.

    Supported apps: FaceTime, Calendar, Photos, Mail, Notes, Reminders,
    Clock, TV, Games, App Store, Maps, Health, Wallet, Settings,
    Phone, Safari, Messages, Music.
    """
    pos = app_position(name)
    if pos is None:
        raise ValueError(
            f"Unknown app '{name}'. This tool only supports 18 preset system apps. "
            f"Use launch_app(bundle_id) for third-party apps, or open_url() for URL schemes."
        )
    # Go home first to ensure we're on page 1
    _require_ok(_client().key("home"))
    import time; time.sleep(0.5)
    return _require_ok(_client().tap(pos[0], pos[1]))


@mcp.tool()
def tap_back() -> str:
    """Tap the iOS navigation back button (top-left corner)."""
    return _require_ok(_client().tap(BACK_BUTTON[0], BACK_BUTTON[1]))


@mcp.tool()
def open_search() -> str:
    """Tap the Search bar on the home screen."""
    return _require_ok(_client().tap(SEARCH_BAR[0], SEARCH_BAR[1]))


@mcp.tool()
def scroll_down() -> str:
    """Scroll down on the current screen."""
    return _require_ok(_client().swipe(**SCROLL_DOWN))


@mcp.tool()
def scroll_up() -> str:
    """Scroll up on the current screen."""
    return _require_ok(_client().swipe(**SCROLL_UP))


@mcp.tool()
def open_notification_center() -> str:
    """Swipe down from the top-left to open Notification Center."""
    return _require_ok(_client().swipe(**NOTIFICATION_CENTER))


@mcp.tool()
def open_control_center() -> str:
    """Swipe down from the top-right to open Control Center."""
    return _require_ok(_client().swipe(**CONTROL_CENTER))


@mcp.tool()
def open_app_switcher() -> str:
    """Slow swipe up from bottom to open the App Switcher."""
    return _require_ok(_client().swipe(**APP_SWITCHER))


@mcp.tool()
def swipe_to_next_page() -> str:
    """Swipe left to go to the next home screen page."""
    return _require_ok(_client().swipe(**NEXT_PAGE))


@mcp.tool()
def swipe_to_previous_page() -> str:
    """Swipe right to go to the previous home screen page."""
    return _require_ok(_client().swipe(**PREV_PAGE))


# ---------------------------------------------------------------------------
# Layer 4: Raw interaction (for app-specific UI)
# ---------------------------------------------------------------------------

@mcp.tool()
def tap(x: int, y: int) -> str:
    """Tap at specific pixel coordinates on the screen.

    Coordinates use the full-resolution pixel space (1290x2796), regardless
    of whether you took a compact or full-resolution screenshot. If you
    identified a target in a compact screenshot (430x932), multiply the
    coordinates by 3 to get the tap position.

    Args:
        x: Horizontal pixel coordinate (0=left, 1290=right)
        y: Vertical pixel coordinate (0=top, 2796=bottom)
    """
    return _require_ok(_client().tap(x, y))


@mcp.tool()
def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Swipe from one point to another.

    Coordinates are in pixels matching the screenshot dimensions (1290x2796).

    Args:
        x1: Start X coordinate
        y1: Start Y coordinate
        x2: End X coordinate
        y2: End Y coordinate
        duration_ms: Swipe duration in milliseconds (default 300)
    """
    return _require_ok(_client().swipe(x1, y1, x2, y2, ms=duration_ms))


# ---------------------------------------------------------------------------
# Layer 5: App management
# ---------------------------------------------------------------------------

@mcp.tool()
def install_ipa(path: str) -> str:
    """Install an IPA file onto the iOS VM.

    The IPA will be automatically signed and installed. No Apple Developer
    account is needed — the guest uses ldid for ad-hoc signing.

    Args:
        path: Absolute path to the .ipa file on the host machine
    """
    return _require_ok(_client().ipa_install(path))


@mcp.tool()
def launch_app(bundle_id: str, url: str = "") -> str:
    """Launch any app on the iOS VM by its bundle identifier.

    This is the primary way to open apps programmatically. Unlike open_app()
    which only handles 18 preset system apps via coordinate tapping, this tool
    sends a launch request to the iOS guest daemon and works for any installed
    app. Use list_apps() to discover installed apps and their bundle IDs.

    Args:
        bundle_id: The app's bundle identifier (e.g. 'com.apple.mobilesafari',
            'com.bytedance.commercepro'). Use list_apps() to find it.
        url: Optional URL to open with the app (URL Scheme or Universal Link)
    """
    resp = _client().app_launch(bundle_id, url=url or None)
    _require_ok(resp)
    pid = resp.get("pid", 0)
    return f"Launched {bundle_id} (pid: {pid})"


@mcp.tool()
def terminate_app(bundle_id: str) -> str:
    """Terminate a running app on the iOS VM.

    Args:
        bundle_id: The app's bundle identifier
    """
    return _require_ok(_client().app_terminate(bundle_id))


@mcp.tool()
def list_apps(filter: str = "user") -> str:
    """List installed apps on the iOS VM.

    Args:
        filter: Filter type — 'all', 'user', 'system', or 'running'
    """
    resp = _client().app_list(filter=filter)
    _require_ok(resp)
    apps = resp.get("apps", [])
    lines = []
    for app in apps:
        line = f"{app.get('name', '?')} ({app.get('bundle_id', '?')})"
        if app.get("version"):
            line += f" v{app['version']}"
        if app.get("state") == "running":
            line += f" [running, pid={app.get('pid', '?')}]"
        lines.append(line)
    return "\n".join(lines) if lines else "No apps found."


# ---------------------------------------------------------------------------
# Layer 6: File operations
# ---------------------------------------------------------------------------

@mcp.tool()
def push_file(local_path: str, remote_path: str) -> str:
    """Push a file from the host machine to the iOS VM guest filesystem.

    Args:
        local_path: Path to the source file on the host
        remote_path: Destination path on the iOS VM (e.g. '/var/mobile/Documents/data.json')
    """
    resp = _client().file_push(local_path, remote_path)
    _require_ok(resp)
    size = resp.get("size", 0)
    return f"Pushed {size} bytes to {remote_path}"


@mcp.tool()
def pull_file(remote_path: str, local_path: str) -> str:
    """Pull a file from the iOS VM guest filesystem to the host machine.

    Args:
        remote_path: Path to the file on the iOS VM
        local_path: Destination path on the host machine
    """
    resp = _client().file_pull(remote_path, local_path)
    _require_ok(resp)
    size = resp.get("size", 0)
    return f"Saved {size} bytes to {local_path}"


# ---------------------------------------------------------------------------
# Layer 7: Clipboard & URL
# ---------------------------------------------------------------------------

@mcp.tool()
def set_clipboard(text: str) -> str:
    """Set the iOS VM clipboard content. This is NOT direct text input.

    This tool only places text on the clipboard. To actually input text into
    a UI field, you must then perform the paste gesture manually:
      1. Tap the target text field to focus it
      2. Call set_clipboard(text)
      3. Long-press on the field (tap with ~1s hold), then tap "Paste"

    Note: This clipboard-then-paste workflow is fragile and multi-step.
    For reliable direct text input, the rpc-project integration
    (accessibility.insert_text) is needed — see Phase 3.3 in PROGRESS.md.

    Args:
        text: The text to place on the clipboard
    """
    return _require_ok(_client().clipboard_set(text))


@mcp.tool()
def open_url(url: str) -> str:
    """Open a URL on the iOS VM via the system URL handler.

    Supports web URLs (https://...) and custom URL schemes (myapp://...).

    Args:
        url: The URL to open
    """
    return _require_ok(_client().open_url(url))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
