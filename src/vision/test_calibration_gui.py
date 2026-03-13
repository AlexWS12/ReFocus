"""
Simple test GUI for phone calibration.
Run with: uv run python src/vision/test_calibration_gui.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from phone_calibration import PhoneCalibration


class CalibrationTestGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Phone Calibration Test")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        self.calibrator = None
        self.calibration_result = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Title
        title = tk.Label(self.root, text="Phone Detection Calibration", font=("Arial", 16, "bold"))
        title.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(
            self.root, 
            text="Click 'Start Calibration', place the phone in the box,\nthen rotate right and left slowly.",
            font=("Arial", 10),
            justify="center"
        )
        instructions.pack(pady=10)
        
        # Calibration button
        self.calibrate_btn = ttk.Button(
            self.root, 
            text="Start Calibration", 
            command=self._start_calibration
        )
        self.calibrate_btn.pack(pady=20)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Status: Ready", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # Results frame
        self.results_frame = tk.LabelFrame(self.root, text="Results", padx=10, pady=10)
        self.results_frame.pack(pady=10, padx=20, fill="x")
        
        self.result_text = tk.Label(self.results_frame, text="No calibration yet", font=("Arial", 9), justify="left")
        self.result_text.pack()
    
    def _start_calibration(self):
        """Start calibration in a separate thread."""
        self.calibrate_btn.config(state="disabled")
        self.status_label.config(text="Status: Calibrating...")
        self.result_text.config(text="Place your phone in the guide box to auto-start...")
        
        # Run calibration in background thread
        thread = threading.Thread(target=self._run_calibration, daemon=True)
        thread.start()
    
    def _run_calibration(self):
        """Run the actual calibration (in background thread)."""
        try:
            self.calibrator = PhoneCalibration("yolo26n.pt")
            result = self.calibrator.run_calibration(target_detections=15)
            self.calibration_result = result
            
            # Update UI from main thread
            self.root.after(0, lambda: self._show_results(result))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
    
    def _show_results(self, result):
        """Display calibration results."""
        self.calibrate_btn.config(state="normal")
        
        if result.get("error"):
            self.status_label.config(text=f"Status: {result['error']}")
            self.result_text.config(text=result["error"])
            return
        
        if result.get("success"):
            self.status_label.config(text="Status: Calibration successful!")
            data = result.get("data", {})
            text = (
                f"Lighting: {data.get('lighting_quality', 'N/A')}\n"
                f"Avg Confidence: {data.get('avg_confidence', 'N/A')}\n"
                f"Optimal Threshold: {data.get('optimal_conf_threshold', 'N/A')}\n"
                f"Detections: {data.get('detections_count', 0)}"
            )
            self.result_text.config(text=text)
            
            # Show recommendation
            messagebox.showinfo("Calibration Complete", result.get("recommendation", "Done!"))
        else:
            self.status_label.config(text="Status: Calibration failed")
            self.result_text.config(text=f"{result.get('message', 'Failed')}\n{result.get('suggestion', '')}")
    
    def _show_error(self, error_msg):
        """Display error message."""
        self.calibrate_btn.config(state="normal")
        self.status_label.config(text="Status: Error")
        self.result_text.config(text=f"Error: {error_msg}")
        messagebox.showerror("Error", error_msg)
    
    def run(self):
        """Start the GUI."""
        self.root.mainloop()


if __name__ == "__main__":
    app = CalibrationTestGUI()
    app.run()
