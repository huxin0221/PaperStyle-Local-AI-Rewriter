"""Temporary recovery loader; restore gui.py from IDE Local History."""
import marshal
import sys
from pathlib import Path

if sys.version_info[:2] != (3, 11):
    raise RuntimeError("UI recovery requires Python 3.11; restore gui.py from PyCharm Local History.")
with (Path(__file__).with_name('gui_recovery.pyc')).open('rb') as backup:
    backup.read(16)
    exec(marshal.load(backup), globals())

# Editable layout customization around the recovered UI implementation.
_RecoveredWindow = Window


class Window(_RecoveredWindow):
    def build_library(self):
        super().build_library()
        content = self.library_scroll.widget()
        body = content.layout()
        container = W.QWidget()
        outer = W.QVBoxLayout(container)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(8)

        for _ in range(2):
            item = body.takeAt(0)
            widget = item.widget()
            widget.setSizePolicy(W.QSizePolicy.Preferred, W.QSizePolicy.Fixed)
            outer.addWidget(widget)

        # Retain both complete input pages and their original controls.
        source_item = body.takeAt(0)
        self.paper_sources.setMinimumHeight(0)
        self.source_scroll = W.QScrollArea()
        self.source_scroll.setWidgetResizable(True)
        self.source_scroll.setFrameShape(W.QFrame.NoFrame)
        self.paper_sources.setMinimumHeight(540)
        self.source_scroll.setWidget(self.paper_sources)
        outer.addWidget(self.source_scroll, 3)

        train_item = body.takeAt(0)
        train_row = train_item.layout()
        while train_row.count() > 1:
            item = train_row.takeAt(0)
            if item.widget():
                item.widget().hide()
        self.profile_name.setText('Frozen Style')

        # Details remain available below the papers without squeezing inputs.
        self.library_scroll.setMinimumHeight(100)
        self.library_scroll.setMaximumHeight(200)
        index = self.tabs.indexOf(self.library_scroll)
        title = self.tabs.tabText(index)
        self.tabs.removeTab(index)
        outer.addWidget(self.library_scroll, 1)
        outer.addLayout(train_row)
        self.tabs.insertTab(index, container, title)
        # QTabWidget hides removed pages; reparenting does not clear that state.
        self.library_scroll.show()
        self.paper_sources.show()