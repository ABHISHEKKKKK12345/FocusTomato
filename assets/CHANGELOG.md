# FocusTomato Changelog

## v1.0.0 — UI/UX Polish Release (2026)

### Visual & Design Fixes
- Fixed accent-hover colour bug: hover state was identical to base colour (now properly lightened)
- Fixed `QRectF` imported from wrong module (`QtGui` → `QtCore`) — caused import crash
- Removed dead code: unused `QPolygon`, `QPoint`, `leaf_pts_*` variables in `main_window.py`
- Removed unused `TYPOGRAPHY`, `QSize`, `QPoint` imports from `main_window.py`
- Fixed `QGroupBox` title now has correct background colour (no longer transparent on light theme)
- Added `#SectionHeader` QSS rule so section labels render in secondary colour, not primary
- Added `#EmptyStateLabel` and `#SettingDesc` QSS rules for consistent secondary text styling

### Typography & Readability
- Raised minimum font size across history list (10px → 11px+ accessible floor)
- StatCard value font reduced from 26pt to 24pt to prevent overflow on small windows
- Cycle label reworded from `"0 / 4 sessions until long break"` → `"Session 1 of 4"`
- Task banner placeholder reworded from `"No task selected"` → `"No task selected — go to Tasks to pick one"`
- Settings combo options capitalised: `dark/light` → `Dark/Light`, `gentle/classic/minimal` → `Gentle chime / Classic beep / Minimal tone`

### UX & Interaction
- Timer Reset button: replaced ambiguous `↺` symbol with text label `"Reset"`
- Timer Skip button: replaced ambiguous `⏭` media icon with text label `"Skip"`
- PillButton: added unchecked text colour (was inheriting and invisible on some themes)
- PillButton: added `:hover` state with accent border preview before selection
- `AnimatedToggle`: enlarged to 48×26 for better click target; added `PointingHandCursor`
- `IconButton`: min size raised from 32×32 to 36×36 for click target compliance
- Task action buttons: "Set active" → `"▷ Focus"` / `"▣ Focusing"` (clear affordance)
- Task "complete" button renamed to `"Done"` with green styling
- Task item: replaced 4-always-visible icon buttons with clear labelled buttons
- Task item: active task now shown with accent left-border strip instead of dot only
- Task item: added mini pomodoro progress bar (completed/estimated) per task
- Task dialog: validation now shows red border on title field + visible error message
- Task dialog: OK button renamed to `"Add Task"` / `"Save Changes"` contextually
- Dashboard: stat cards reorganised into Today / This Week / All Time sections
- Dashboard: time values use human format (`"75 min"` → `"1h 15m"`, `"3.2h"` etc.)
- Dashboard: streak card accented green when ≥ 3 days
- Dashboard: chart total label added (`"12 sessions · 300 min this week"`)
- Dashboard: history timestamps now show `"Today 14:30"` / `"Yesterday 09:00"` relative labels
- Dashboard: entire panel wrapped in scroll area (no clipping on small windows)
- Settings: `_ToggleRow` now correctly positions thumb on load (was always showing unchecked position)
- Settings: sound theme combo uses `addItem(label, data)` pattern to decouple display from stored value
- Settings: reset confirmation dialog reworded to clarify tasks/history are not affected
- Settings: clear history dialog reworded to clarify settings/tasks are not affected
- Settings: `"Notifications"` tab renamed to `"Alerts"` (fits tab bar without truncation)
- ProgressRing: `"Paused"` state is now separate from sub-text — task name preserved during pause
- ProgressRing: session-type label coloured with ring accent colour (not always grey)
- ProgressRing: text layout uses proportional sizing from ring diameter (no fixed pixel positions)
- BarChart: added empty-state placeholder bars with day labels when no data
- BarChart: added value labels above non-zero bars
- BarChart: today's bar is full-brightness; prior days are 130/255 alpha (was 160/255)
- `SessionDotRow`: width is now dynamic based on count (was fixed 200px)
- Dark theme: base darkened from `#0F0F0F` to `#111111` for better OLED rendering
- Dark theme: surface layers slightly adjusted for clearer depth hierarchy
- QSS: scrollbar made 8px wide with transparent background (easier to grab)
- QSS: `QComboBox` items have `min-height: 28px` for click target compliance
- QSS: `QSlider` handle enlarged to 18×18 with hover expansion to 20×20
- QSS: `QFrame[frameShape]` separator fixed (was rendering incorrectly on some platforms)
- QSS: added `min-height: 32px` to base `QPushButton` to prevent too-small buttons

### Architecture
- `main_window.py`: `_make_tomato_icon` cleaned up (removed dead leaf variable assignments)
- `task_panel.py`: `_PomoProgressBar` added as dedicated painter widget
- `task_panel.py`: `TaskItemWidget` uses `QVBoxLayout` root with accent strip for cleaner layout
- `dashboard_widget.py`: outer `QScrollArea` wrapping ensures dashboard never clips content
- All files: no circular imports confirmed via full import-order test

### Bug Fixes
- `QRectF` was imported from `PyQt6.QtGui` in `task_panel.py` — import error on all platforms (fixed)
- `QPolygon` dead import inside `_make_tomato_icon` function (removed)
- `opacity:` CSS property used in `TaskItemWidget` QSS — not supported in QSS; replaced with colour-based dimming
- `_ToggleRow.set_checked()` method added (was missing; `_load_values` was setting toggle state without updating thumb position)
- Settings combo save/load used `.currentText()` which broke when display names differed from stored values; fixed with index-based mapping
