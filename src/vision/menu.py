
import importlib
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
import questionary
import sys

# When menu.py is run directly (python src/vision/menu.py), only src/vision/
# lands on sys.path and cross-package imports like src.intelligence.* fail.
# Insert the project root so all src.* packages are always resolvable.
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

if sys.platform == "win32":
    import msvcrt
else:
    msvcrt = None

def _import_symbol(primary_module: str, fallback_module: str, symbol: str):
    """Import symbol from project-root path first, then direct-run fallback path."""
    for module_path in (primary_module, fallback_module):
        try:
            return getattr(importlib.import_module(module_path), symbol)
        except (ModuleNotFoundError, AttributeError):
            continue
    raise ImportError(
        f"Cannot resolve {symbol} from {primary_module} or {fallback_module}"
    )


console = Console()


def launch_camera() -> None:
    """Run the camera loop with phone and attention overlays.

    Requires phone calibration to have been run at least once — the detection
    thresholds (YOLO confidence, appearance similarity gate, fallback gate) are
    loaded exclusively from the calibration bundle. If the bundle is missing the
    user is redirected to calibrate before the camera starts.
    """
    # OpenCV import is local so calibration-only menu usage stays lightweight.
    import cv2 as cv

    # Camera and SessionManager are imported lazily so calibration paths do not
    # instantiate or even import camera-specific runtime dependencies.
    Camera = _import_symbol("src.vision.camera", "camera", "Camera")
    SessionManager = _import_symbol(
        "src.intelligence.session_manager", "session_manager", "SessionManager"
    )

    # Guard: refuse to start if the user has never calibrated.
    # Thresholds have no hardcoded defaults — calibration must run first.
    PhoneCalibration = _import_symbol(
        "src.vision.detectors.phone_calibration",
        "detectors.phone_calibration",
        "PhoneCalibration",
    )
    bundle_path = PhoneCalibration.get_few_shot_bundle_path()
    import os
    if not os.path.exists(bundle_path):
        console.print(
            "[yellow]Phone calibration has not been run yet.[/yellow]\n"
            "Please run [bold]Calibrate phone detection[/bold] first so the camera "
            "knows what your phone looks like and what confidence thresholds to use."
        )
        return

    # SessionManager attaches to the shared intelligence DB lazily; the app layer
    # is responsible for bootstrapping persistent state when running the full UI.
    session_manager = SessionManager()
    session_manager.start_session()

    cam = Camera(session_manager=session_manager)
    console.print("[bold cyan]Starting camera. Press Q in video window to exit.[/bold cyan]")

    try:
        while True:
            data = cam.read_frame()
            if data is None:
                break
            _, annotated = data  # data is (raw_frame, annotated_frame); we only need the overlay
            cv.imshow("StudyWidget Vision", annotated)
            # waitKey(1) keeps the event loop alive; 0xFF mask strips platform-specific high bits
            if cv.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cam.release()
        # End session after camera release so any flushed distractions are included.
        try:
            session_manager.end_session()
        except Exception:
            pass


def calibrate_phone_detection() -> None:
    """Run the existing YOLO phone calibration flow."""
    PhoneCalibration = _import_symbol(
        "src.vision.detectors.phone_calibration",
        "detectors.phone_calibration",
        "PhoneCalibration",
    )
    result = PhoneCalibration().run_calibration()
    if result.get("success"):
        console.print(f"[green]Phone calibration complete:[/green] {result}")
    else:
        console.print(f"[yellow]Phone calibration did not complete:[/yellow] {result}")


def calibrate_gaze_center() -> None:
    """Calibrate neutral gaze center offsets used by attention tracker."""
    GazeCalibrator = _import_symbol(
        "src.vision.Trackers.gaze_calibration",
        "Trackers.gaze_calibration",
        "GazeCalibrator",
    )
    result = GazeCalibrator().run()
    if result.get("success"):
        console.print(
            "[green]Gaze center saved[/green] "
            f"(yaw={result['yaw_center_deg']:.2f}, pitch={result['pitch_center_deg']:.2f}, roll={result['roll_center_deg']:.2f})"
        )
    else:
        console.print(f"[yellow]Gaze calibration did not complete:[/yellow] {result}")


def main() -> None:
    """Minimal modular vision menu."""
    while True:
        console.print(
            Panel.fit(
                "1) Launch Camera\n2) Calibrate phone detection\n3) Calibrate gaze center\n4) Exit",
                title="Vision Menu",
            )
        )

        # Drain any keys that were pressed while the previous option was running so
        # they don't immediately fire the next questionary prompt.
        if msvcrt:
            while msvcrt.kbhit():
                msvcrt.getch()

        choice = questionary.select(
            "Choose an option:",
            choices=[
                "1) Launch Camera",
                "2) Calibrate phone detection",
                "3) Calibrate gaze center",
                "4) Exit",
            ],
        ).ask()

        # choice is None when the user hits Ctrl-C inside questionary.
        if choice is None or choice.startswith("4"):
            console.print("[cyan]Exiting vision menu.[/cyan]")
            break

        if choice.startswith("1"):
            launch_camera()
        elif choice.startswith("2"):
            calibrate_phone_detection()
        elif choice.startswith("3"):
            calibrate_gaze_center()


if __name__ == "__main__":
    main()
