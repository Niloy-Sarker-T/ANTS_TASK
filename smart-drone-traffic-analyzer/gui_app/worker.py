from PyQt5.QtCore import QThread, pyqtSignal
from app.processor import process_video


class Worker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, input_path, output_dir):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir

    def run(self):
        try:
            def callback(current, total):
                percent = int((current / total) * 100)
                self.progress.emit(percent)

            result = process_video(
                self.input_path,
                self.output_dir,
                callback
            )

            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))