from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCharts import (
    QChart, QChartView, QHorizontalBarSeries, QBarSet,
    QBarCategoryAxis, QValueAxis,
)

from src.experience.widgets.centered_label import CenteredLabel

# top bar gets an accent colour; the rest are progressively more muted
_BAR_COLORS = [
    QColor("#3b7deb"),
    QColor("#5a9cf0"),
    QColor("#7ab2f5"),
    QColor("#9ac8f8"),
    QColor("#b8dcfb"),
]


class FeatureImportanceWidget(QFrame):

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.addWidget(CenteredLabel("What Drives Your Score"))

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.legend().hide()
        self._chart.setMargins(QMargins(4, 4, 4, 4))

        self._chart_view = QChartView(self._chart)
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setStyleSheet("background: transparent; border: none;")
        self._chart_view.setMinimumHeight(180)
        layout.addWidget(self._chart_view)

        self._label = CenteredLabel("", secondary=True)
        layout.addWidget(self._label)

        self.refresh(parent.data)

    def refresh(self, data):
        pa = data.get("pattern_analysis")

        self._chart.removeAllSeries()
        for axis in self._chart.axes():
            self._chart.removeAxis(axis)

        if pa is None:
            self._label.setStyleSheet("font-size: 15px;")
            total = (data.get("session_analytics") or {}).get("total_sessions", 0) or 0
            if total < 10:
                self._label.setText(f"Need {10 - total} more sessions for ML analysis")
            else:
                self._label.setText("Analysing...")
            return
        self._label.setStyleSheet("")

        fi       = pa.get("ml_feature_importance", {})
        features = fi.get("features", [])

        if not features or fi.get("error"):
            self._label.setText("Not enough data for feature analysis")
            return

        # show top 5 features
        top5 = features[:5]
        categories = []
        series = QHorizontalBarSeries()

        for i, feat in enumerate(top5):
            bar_set = QBarSet(feat["label"])
            bar_set.append(feat["importance_pct"])
            bar_set.setColor(_BAR_COLORS[i % len(_BAR_COLORS)])
            series.append(bar_set)
            categories.append(feat["label"])

        self._chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        self._chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        max_pct = top5[0]["importance_pct"]
        axis_x = QValueAxis()
        axis_x.setRange(0, max_pct * 1.2)
        axis_x.setLabelFormat("%.0f%%")
        axis_x.setGridLineColor(QColor(200, 200, 200, 60))
        self._chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        top_label = fi.get("top_factor", "")
        r2        = fi.get("r2_score")
        r2_str    = f"  ·  model fit R²={r2:.2f}" if r2 is not None else ""
        self._label.setText(f"Top factor: {top_label}{r2_str}")
