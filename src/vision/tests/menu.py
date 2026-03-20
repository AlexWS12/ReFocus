
import cv2 as cv
import os
import sys
from rich.console import Console
from rich.panel import Panel
import questionary
import msvcrt

# menu.py now lives in src/vision/tests, so add src/vision to sys.path so
# sibling imports (camera, detectors, Trackers) still resolve when run directly.
_vision_dir = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
if _vision_dir not in sys.path:
    sys.path.insert(0, _vision_dir)

from camera import Camera
from detectors.phone_calibration import PhoneCalibration
from Trackers.gaze_calibration import GazeCalibrator

# Resolve the sibling intelligence package regardless of whether this file is
# launched directly from src/vision or imported from the project root.
_intel_dir = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "intelligence")
)
if _intel_dir not in sys.path:
    sys.path.insert(0, _intel_dir)

from database import get_database
from session_manager import SessionManager


console = Console()


def initialize_database() -> None:
    """Create the shared SQLite database object before showing the menu."""
    # get_database() constructs the singleton on first call, creating tables if needed.
    get_database()


def launch_camera() -> None:
    """Run the camera loop with phone and attention overlays."""
    # Create and start a session so camera distraction events are written to data.db.
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
    result = PhoneCalibration().run_calibration()
    if result.get("success"):
        console.print(f"[green]Phone calibration complete:[/green] {result}")
    else:
        console.print(f"[yellow]Phone calibration did not complete:[/yellow] {result}")


def calibrate_gaze_center() -> None:
    """Calibrate neutral gaze center offsets used by attention tracker."""
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
    initialize_database()

    while True:
        console.print(
            Panel.fit(
                "1) Launch Camera\n2) Calibrate phone detection\n3) Calibrate gaze center\n4) Exit",
                title="Vision Menu",
            )
        )

        # Drain any keys that were pressed while the previous option was running so
        # they don't immediately fire the next questionary prompt.
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
