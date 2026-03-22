
import cv2 as cv
from rich.console import Console
from rich.panel import Panel
import questionary
import sys

if sys.platform == "win32":
    import msvcrt
else:
    msvcrt = None




from camera import Camera
from detectors.phone_calibration import PhoneCalibration
from Trackers.gaze_calibration import GazeCalibrator


console = Console()


def launch_camera() -> None:
    """Run the camera loop with phone and attention overlays."""
    cam = Camera()
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
