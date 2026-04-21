import os
import sys
import uuid

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QProgressBar, QMessageBox
)

from .worker import Worker


class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Smart Drone Traffic Analyzer")
        self.setGeometry(300, 200, 500, 300)

        self.layout = QVBoxLayout()

        self.label = QLabel("Select a video to start processing")
        self.layout.addWidget(self.label)

        self.btn = QPushButton("Choose Video")
        self.btn.clicked.connect(self.select_file)
        self.layout.addWidget(self.btn)

        self.start_btn = QPushButton("Start Processing")
        self.start_btn.clicked.connect(self.start)
        self.start_btn.setEnabled(False)
        self.layout.addWidget(self.start_btn)

        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)

        self.setLayout(self.layout)

        self.file_path = None
        self.worker = None

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Video", "", "Video Files (*.mp4)"
        )

        if file:
            self.file_path = file
            self.label.setText(f"Selected: {file}")
            self.start_btn.setEnabled(True)

    def start(self):
        if not self.file_path:
            return

        job_id = str(uuid.uuid4())
        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        self.worker = Worker(self.file_path, output_dir)

        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.done)
        self.worker.error.connect(self.show_error)

        self.worker.start()

        self.label.setText("Processing...")

    def update_progress(self, val):
        self.progress.setValue(val)

    def done(self, result):
        self.label.setText("Processing Complete")

        QMessageBox.information(
            self,
            "Done",
            f"Total Vehicles: {result['total_unique']}\n"
            f"Duration: {result['processing_duration']} sec"
        )

    def show_error(self, msg):
        QMessageBox.critical(self, "Error", msg)


app = QApplication(sys.argv)
window = App()
window.show()
sys.exit(app.exec_())