## Experience module overview

The `src/experience` package implements the main desktop user interface for the Study Tracker. It is a PySide6 (Qt) application composed of a main window with a sidebar, a top bar showing gamified progress, and several pages backed by small, focused widgets.

### Folder structure

- **`main_window.py`**: Defines the `MainWindow` class, the central window of the app. It:
  - Creates the main horizontal layout with the sidebar on the left and the top‑bar + pages area on the right.
  - Owns the `QStackedWidget` that hosts all pages (`Dashboard`, `Session`, `Report`, `VirtualPet`, `Achievements`).
- **`side_bar.py`**: Implements the `Sidebar` widget. It:
  - Displays navigation buttons (`Dashboard`, `Session`, `Report`, `Virtual Pet`, `Achievement`).
  - Switches the visible page in `MainWindow.pages_stack` when a button is clicked.
- **`button.py`**: Simple wrapper around `QPushButton`, used for all navigation and call‑to‑action buttons to keep styling and behavior consistent.
- **`pet_window.py`**: Defines the always‑on‑top, frameless floating `petWindow` that shows the virtual pet during a focus session. The user can drag it around and double‑click to end the session and return to the main window.

- **`pages/`**: High‑level screens that the user navigates between via the sidebar:
  - **`dashboard.py`** (`Dashboard`):
    - Lays out core summary widgets (`AvgFocusTime`, `PetView`, `Calendar`, `PreviousSession`) in a grid.
    - Provides a **Start Session** button that hides the main window, shows the floating `petWindow`, and positions it.
  - **`session.py`** (`Session`):
    - Placeholder page for deeper in‑session controls and details.
    - Currently shows a “Session” placeholder.
  - **`report.py`** (`Report`):
    - Shows long‑term analytics widgets (`LifetimeFocus`, `TotalSessions`, `LongestFocus`, `TotalExp`) in a grid.
  - **`virtualPet.py`** (`VirtualPet`):
    - Placeholder page focused on the pet, currently just a “Virtual Pet” label.
    - Intended for pet customization, status, and interaction UI shared with other groups.
  - **`achievements.py`** (`Achievements`):
    - Placeholder page that currently shows an “Achievements” label.
    - Entry point for achievement lists, badges, and reward progress.

- **`widgets/`**: Reusable, focused UI components used across pages:
  - **`top_bar.py`** (`TopBar`):
    - Horizontal bar at the top of the main window.
    - Displays the current `Level`, `XP`, and `Coins` based on data loaded by `MainWindow`.
  - **`centered_label.py`** (`CenteredLabel`):
    - A `QLabel` wrapper with centered alignment used across many simple widgets and placeholder pages.
  - **`avg_focus_time.py`** (`AvgFocusTime`):
    - Shows “Average Focus Time” and the current value (in minutes) from `dashboard` data.
  - **`pet_view.py`** (`PetView`):
    - Displays the pet image (`Panther.png`) scaled to 120×120.
    - Used on the dashboard to visually connect the pet with the rest of the stats.
  - **`calendar.py`** (`Calendar`):
    - A compact `QCalendarWidget` used on the dashboard.
    - Styling is further refined in `style/theme.qss`.
  - **`previous_session.py`** (`PreviousSession`):
    - Shows summary metrics for the most recent session: score, focused percentage, and number of events.
    - Reads its data from `parent.data["previous_session_data"]`.
  - **`lifetime_focus.py`** (`LifetimeFocus`):
    - Displays total focus time across all sessions in seconds from `session_analytics.lifetime_focus_seconds`.
  - **`total_sessions.py`** (`TotalSessions`):
    - Shows the total number of sessions from `session_analytics.total_sessions`.
  - **`longest_focus.py`** (`LongestFocus`):
    - Shows the longest single focus streak in seconds from `session_analytics.longest_focus_seconds`.
  - **`total_exp.py`** (`TotalExp`):
    - Displays the accumulated experience (`total_exp`) calculated in the `Report` page.
- **`static/`**:
  - **`Panther.png`**: Current pet sprite used by both `PetView` and `petWindow`.
- **`style/theme.qss`**:
  - Qt stylesheet that customizes the look of specific widgets, currently focused on `QCalendarWidget` but it will be used for the rest of the UI in the future.

### How to launch the experience app

- **From the project root**, you can run the full UI by executing `main.py`.

  ```bash
  python main.py
  ```

- `main.py`:
  - Instantiates the shared `Database` layer.
  - Creates and runs the custom `QApplication` from `src.core.qApplication`.
  - The `QApplication` is responsible for creating `MainWindow` and the floating `petWindow`.

### `DatabaseReader` and how UI data is loaded

- **`src.core.database_reader.DatabaseReader`** (used by the experience layer) is the adapter between the raw `Database` and the UI. It:
  - Exposes high‑level, UI‑ready methods such as `get_topbar_data()`, `load_dashboard_data()`, and `load_report_data()`.
  - Hides the underlying schema and query details from widgets and pages.
- **How it is created and shared**:
  - The custom `QApplication` (in `src.core.qApplication`) creates a single `DatabaseReader` instance and stores it on the application object (e.g. `self.database_reader`).
  - All UI components that need database data – including `MainWindow` (for top‑bar data) and pages like `Dashboard` and `Report` – read from this shared instance instead of creating their own.
  - Typical access pattern:
    - `app = QApplication.instance()`
    - `topbar_data = app.database_reader.get_topbar_data()`
    - `dashboard_data = app.database_reader.load_dashboard_data()`
    - `report_data = app.database_reader.load_report_data()`
- **How it is used to render data**:
  - `Dashboard` calls `load_dashboard_data()` once at construction and stores the result in `self.data`, which is then passed implicitly to widgets like `AvgFocusTime`, `PetView`, `Calendar`, and `PreviousSession` through the `parent` reference.
  - `Report` calls `load_report_data()`, enriches the dictionary with `total_exp` (coming from the top‑bar data), and stores it on `self.data` so child widgets like `LifetimeFocus`, `TotalSessions`, `LongestFocus`, and `TotalExp` can read their specific fields.
  - This pattern keeps data loading centralized while allowing each widget to focus only on the small slice of data it needs.