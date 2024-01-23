from PyQt6.QtWidgets import QApplication, QSlider, QListWidgetItem, QLabel, QHBoxLayout, QProgressBar, QLineEdit, QWidget, QMainWindow, QAbstractItemView, QDialog, QFileDialog, QVBoxLayout, QPushButton
from PyQt6 import QtCore, QtGui, QtWidgets, uic
from PyQt6.QtGui import QAction, QDropEvent, QDrag
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import os
from time import sleep
import shutil
from pytube import YouTube
from pytube.exceptions import RegexMatchError, VideoUnavailable
import logging
import logging.handlers
import subprocess
import re


logger = logging.getLogger('EMO_v1_log')
logger.setLevel(logging.DEBUG)

# Create a RotatingFileHandler with a maximum file size of 5 MB
log_filename = 'EMO_v1_log.log'
max_log_size_mb = 5

handler = logging.handlers.RotatingFileHandler(
    filename=log_filename,
    maxBytes=max_log_size_mb * 1024 * 1024,  # Convert MB to bytes
    backupCount=1  # Keep up to 5 backup log files
)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

logger.info(f'PROGRAM START')


class AudioTrackWidget(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        # self.player = None
        # self.audio = None
        self.playing = False

        layout = QHBoxLayout()

        self.play_button = QPushButton("Play")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setVisible(True)

        self.seek_slider.sliderMoved.connect(self.seek_audio)

        self.play_button.setFixedSize(30, 30)
        self.play_button.clicked.connect(self.toggle_audio)

        self.label = QLabel(self.file_name)

        layout.addWidget(self.play_button)
        layout.addWidget(self.seek_slider)
        # layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.update_slider_duration)

    def init(self):
        pass
        # self.player = QMediaPlayer()
        # self.audio = QAudioOutput()
        # self.player.setAudioOutput(self.audio)
        # self.player.positionChanged.connect(self.update_slider_position)
        # self.player.durationChanged.connect(self.update_slider_duration)


    def seek_audio(self):
        # Calculate the desired position in milliseconds based on the slider value
        position = self.seek_slider.value()
        # Seek to the specified position in the audio track
        self.player.setPosition(position)

    def update_slider_position(self, position):
        # Update the slider position as the audio plays
        self.seek_slider.setValue(position)

    def update_slider_duration(self, duration):
        # Set the maximum value of the seek slider to the duration of the audio track
        self.seek_slider.setMaximum(duration)

    def toggle_audio(self):
        if not self.playing:
            self.play_button.setText("Stop")
            self.play_audio()
        else:
            self.play_button.setText("Play")
            self.stop_audio()

    def play_audio(self):
        # Create a QMediaPlayer instance
        if not self.playing:
            self.init()
            self.player.setSource(QUrl.fromLocalFile(self.file_path))
            self.audio.setVolume(50)
            self.playing = True
            self.player.play()

    def stop_audio(self):
        self.player.stop()
        self.playing = False


class AddFolderDialog(QDialog):
    def __init__(self, cwd):
        super().__init__()
        self.setWindowTitle("Add Folder")
        self.layout = QVBoxLayout()
        self.folder_name_input = QLineEdit()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")

        self.layout.addWidget(self.folder_name_input)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.cancel_button)

        self.save_button.clicked.connect(self.save_folder)
        self.cancel_button.clicked.connect(self.close)

        self.setLayout(self.layout)
        self.cwd = cwd

    def save_folder(self):
        folder_name = self.folder_name_input.text()
        if folder_name:
            # Construct the full path by joining folder_name with self.cwd
            new_folder_path = os.path.join(self.cwd, folder_name)

            # Check if the folder already exists
            if not os.path.exists(new_folder_path):
                # Create the new folder
                os.makedirs(new_folder_path)
                print(f"Folder '{folder_name}' created in {self.cwd}")
            else:
                print(f"Folder '{folder_name}' already exists in {self.cwd}")

        self.accept()
class Ui(QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('main_window.ui', self)
        my_menu_button = self.findChild(QAction, "open_music_folder_button")
        # Connect the button's clicked signal to a function
        my_menu_button.triggered.connect(self.open_folder_widget)
        logging.debug(f"Program Start")
        self.target_widget = self.findChild(QWidget, "scrollArea")
        self.url_input = self.findChild(QLineEdit, "yt_dwnldr")
        self.progress_bar = self.findChild(QProgressBar, "progressBar")
        # self.progress_bar.hide()

        self.button_layout = QVBoxLayout(self.target_widget)
        self.back_button.clicked.connect(self.back)
        self.btn_ytdwnld.clicked.connect(self.download_audio)
        self.list_1.itemPressed.connect(self.start_drag)

        self.audio_player = QMediaPlayer()

        self.list_1.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_1.customContextMenuRequested.connect(self.show_context_menu)# Allow multiple item selection

        self.btn_list = []
        self.clicked_item = None
        self.item_data_mapping = {}
        self.internal_move = False
        self.mouse_press_time = None
        self.mouse_release_time = None

        if self.load_saved_folder():
            try:
                self.root_path = self.load_saved_folder()
                self.cwd = self.root_path
                self.run(self.root_path)
            except Exception as e:
                logger.error(e)
        else:
            try:
                self.show()
                self.open_folder_widget()
                self.root_path = self.load_saved_folder()
            except Exception as e:
                logger.error(e)

        self.update_navigation_pane(self.cwd)

    def update_progress(self, stream, chunk, bytes_remaining):
        percentage = int((stream.filesize - bytes_remaining) / stream.filesize * 100)
        print(percentage)
        self.progress_bar.setValue(percentage)

    def download_audio(self):
        # Get the YouTube video URL from the QLineEdit
        video_url = self.url_input.text()

        try:
            # Create a YouTube object
            yt = YouTube(video_url, on_progress_callback=self.update_progress)

            # Get the best audio stream (highest quality MP4 format)
            audio_stream = yt.streams.filter(only_audio=True).first()

            if audio_stream:
                # Set the filename for the audio (use the video title with .mp3 extension)
                audio_filename = yt.title

                # Specify the output path as the current working directory
                output_path = self.cwd

                # Construct the full path for the output file
                output_file_path = os.path.join(output_path, audio_filename)

                self.progress_bar.show()

                # Download the audio stream to a temporary file
                temp_audio_filename = audio_filename + '.temp'
                temp_output_file_path = os.path.join(output_path, temp_audio_filename)
                audio_stream.download(output_path=output_path, filename=temp_audio_filename)

                # Use FFmpeg to convert the temporary audio file to MP3
                cmd = ['ffmpeg', '-i', temp_output_file_path, '-q:a', '0', '-map', 'a', output_file_path + '.mp3']

                # Use subprocess.Popen to capture stderr (FFmpeg progress output)
                ffmpeg_process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)

                # Regular expression to extract progress information from FFmpeg's stderr
                progress_regex = r"size=[\d]+kB time=([\d]+:[\d]+:[\d]+\.[\d]+) "

                while True:
                    line = ffmpeg_process.stderr.readline()
                    if not line:
                        break

                    match = re.search(progress_regex, line)
                    if match:
                        # Extracted progress information
                        time_str = match.group(1)
                        hours, minutes, seconds = map(float, time_str.split(':'))
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        total_duration = int(total_seconds * 1000)  # Convert to milliseconds

                        # Update the progress bar based on the duration
                        self.progress_bar.setValue(total_duration)

                # Wait for FFmpeg to finish the conversion process
                ffmpeg_process.wait()

                # Remove the temporary audio file
                os.remove(temp_output_file_path)

                self.progress_bar.hide()
                print(f"Downloaded and converted audio: {audio_filename}.mp3")
                self.list_viewer()
            else:
                print("No suitable audio stream found for this video.")
        except (VideoUnavailable, RegexMatchError) as e:
            print(f"Error: {e}")
            logger.error(f'download_audio() = {e}')
        except Exception as e:
            print(f"Error downloading audio: {e}")
            logger.error(f'download_audio() = {e}')

    def open_folder_creation_dialog(self):
        dialog = AddFolderDialog(self.cwd)
        dialog.cwd = self.cwd  # Pass the current working directory
        if dialog.exec():
            self.run(self.cwd)

    def back(self):
        if len(self.btn_list) > 0:
            self.btn_list.pop()
            self.cwd = os.path.join(self.root_path, *self.btn_list)
            self.list_viewer()
            self.info_pan.setText(str(self.cwd))
            print(self.btn_list)

    def update_navigation_pane(self, folder_path):
        self.clear_buttons()
        self.cwd = folder_path
        self.list_viewer()

    def open_folder_widget(self):
        folder_dialog = FolderSelectDialog()
        if folder_dialog.exec():
            selected_folder = folder_dialog.selected_folder
            if selected_folder:
                print(f"Selected folder: {selected_folder}")
                self.save_folder(selected_folder)
                self.update_navigation_pane(selected_folder)


    def save_folder(self, root_path):
        try:
            with open("selected_folder.txt", "w") as file:
                file.write(root_path)
                self.root_path = root_path
                print(f'Folder saved!')
        except Exception as e:
            print(f"Error saving folder: {e}")
            logger.error(f'save_folder() = {e}')

    def load_saved_folder(self):
        try:
            with open("selected_folder.txt", "r") as file:
                root_path = file.read().strip()
                if root_path:
                    print(f"Loaded folder: {root_path}")
                    return root_path
        except Exception as e:
            print(f"Error loading folder: {e}")
            logger.error(f'load_saved_folder() = {e}')
            return False

    def run(self, path):
        self.cwd = path
        self.info_pan.setText(str(self.cwd))
        self.clear_buttons()
        path = os.path.normpath(path)
        try:
            print(f"PATH LOADED: {path}")
            dir = os.listdir(path)
            available_height = self.target_widget.height()
            total_buttons = len(dir)

            if total_buttons == 0:
                return  # Avoid division by zero

            button_height = available_height / total_buttons

            for i in dir:
                btn = QPushButton(i)
                btn.setFixedHeight(int(button_height))
                self.button_layout.addWidget(btn)
                btn.clicked.connect(self.button_clicked)
        except Exception as e:
            logger.error(f'run() = {e}')
         # No items in the directory

    def clear_buttons(self):
        layout = self.target_widget.layout()
        if layout:
            # Clear the layout by removing all widgets
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

    def button_clicked(self):
        # Get the text of the button that triggered the signal
        try:
            sender_button = self.sender()
            print(f'Button Clicked CURRENT self.cwd: {self.cwd}')
            if sender_button:
                button_name = sender_button.text()
                if button_name not in self.btn_list:
                    self.btn_list.append(button_name)
            self.cwd = os.path.join(self.root_path, *self.btn_list)
            self.list_viewer()
        except Exception as e:
            logger.error(f'button_clicked = {e}')

    def list_viewer(self):
        self.info_pan.setText(str(self.cwd))
        self.list_1.clear()
        try:
            for root, dirs, files in os.walk(self.cwd):
                for file in files:
                    file_path = os.path.join(root, file)
                    _, file_name = os.path.split(file_path)
                    audio_track_widget = AudioTrackWidget(file_path)
                    item = QListWidgetItem(self.list_1)
                    self.list_1.addItem(file_name)

                    # Add the item and its associated data to the dictionary
                    self.item_data_mapping[file] = root
                    # print(f'FILE: {file}, ROOT: {root}')

                    item.setSizeHint(audio_track_widget.sizeHint())
                    self.list_1.setItemWidget(item, audio_track_widget)
            # print(f"DICTONARY: {self.item_data_mapping}")
            # Connect the itemPressed signal after creating all items
            self.list_1.itemPressed.connect(self.on_item_selected)

            self.run(self.cwd)
        except Exception as e:
            logger.error(f'list_viewer() = {e}')

    def sanitize_key(self, key):
        # This function sanitizes the key (item text) to make it suitable for dictionary use
        # You can customize the sanitization rules based on your requirements
        # Here, we remove spaces and special characters and convert to lowercase
        return key.replace(" ", "_").lower()

    def on_item_selected(self, item):
        try:
            selected_object = item.text()
            # print("MY ITEM", selected_object)
            # Retrieve the directory associated with the selected item using the dictionary
            selected_item_root = self.item_data_mapping.get(selected_object)
            if selected_item_root:
                self.clicked_item = selected_item_root
                # print("Selected Item Root:", selected_item_root)
            else:
                print("Associated data not found for item:", selected_object)
        except Exception as e:
            logger.error(f'on_item_selected() = {e}')

    def show_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        delete_action = QtGui.QAction("Delete", self)
        new_folder = QtGui.QAction("New Folder", self)
        delete_action.triggered.connect(self.delete_selected_item)
        new_folder.triggered.connect(self.open_folder_creation_dialog)

        menu.addAction(delete_action)
        menu.addAction(new_folder)
        menu.exec(self.list_1.mapToGlobal(pos))


    def delete_selected_item(self, item):
        try:
            selected_item = self.list_1.currentItem()
            if selected_item:
                file_path = os.path.join(self.clicked_item, selected_item.text())
                print(f"selected item:{selected_item.text()}")

                # Prompt the user for confirmation before deleting the file
                confirm_delete = QtWidgets.QMessageBox.question(
                    self,
                    "Confirm Deletion",
                    f"Do you want to delete the file:\n{file_path}?",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                )

                if confirm_delete == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        os.remove(file_path)
                        self.list_1.takeItem(self.list_1.row(selected_item))  # Remove the item from the list
                        print(f"Deleted file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting file: {e}")
            self.list_viewer()
        except Exception as e:
            logger.error(f'delete_selected_item() = {e}')

    def dropEvent(self, event: QDropEvent):
        try:
            if event.mimeData().hasUrls() and event.source() != self.list_1:
                # Get the list of dropped file URLs
                urls = event.mimeData().urls()

                # Determine if files are being dragged into or out of list_1
                source_widget = event.source()
                if source_widget == self.list_1.viewport():
                    # Files are being dragged out of list_1 (removing files)

                    for url in urls:
                        file_name = url.toLocalFile()
                        item = self.list_1.findItems(file_name, Qt.MatchExactly)
                        if item:
                            # Remove the item from the list (file deletion)
                            self.list_1.takeItem(self.list_1.row(item[0]))
                            os.remove(file_name)
                            print(f"Deleted file: {file_name}")
                else:
                    # Files are being dragged into list_1 (adding files)

                    target_directory = self.cwd  # Get the current working directory

                    for url in urls:
                        file_path = url.toLocalFile()
                        file_name = os.path.basename(file_path)
                        target_file_path = os.path.join(target_directory, file_name)

                        if not os.path.exists(target_file_path):
                            # Check if the target directory is different from the source directory
                            if target_directory != self.clicked_item:
                                event.acceptProposedAction()
                                try:
                                    # Copy the file to the target directory
                                    shutil.copy(file_path, target_directory)
                                    print(f"Copied file: {file_name} to {target_directory}")
                                except Exception as copy_error:
                                    print(f"Error copying file: {copy_error}")
                                    logger.error(f'dropEvent() - Copy Error = {copy_error}')
                            else:
                                # Internal move, ignore the event
                                event.ignore()
                                return
                        else:
                            print(f"File '{file_name}' already exists in {target_directory}")
                            event.ignore()
                            break  # Ignore the entire event if any file exists
                self.list_viewer()
            else:
                event.ignore()
        except Exception as e:
            print(f"Error in dropEvent: {e}")
            logger.error(f'dropEvent() - Error = {e}')

    def dragEnterEvent(self, event: QDropEvent):
        try:
            if event.mimeData().hasUrls() and event.source() != self.list_1:
                urls = event.mimeData().urls()
                target_directory = self.cwd  # Get the current working directory

                for url in urls:
                    file_path = url.toLocalFile()
                    file_name = os.path.basename(file_path)
                    target_file_path = os.path.join(target_directory, file_name)

                    if not os.path.exists(target_file_path):
                        # Check if the target directory is different from the source directory
                        event.acceptProposedAction()
                    else:
                        # Ignore the event for any internal move (within the same directory)
                        event.ignore()
                        return
        except Exception as e:
            logger.error(f'dragEnterEvent() = {e}')

    def start_drag(self, item):
        try:
            self.on_item_selected(item)
            if item:
                file_path = os.path.join(self.clicked_item, item.text())

                if not self.internal_move:
                    mime_data = QMimeData()
                    mime_data.setUrls([QtCore.QUrl.fromLocalFile(file_path)])

                    drag = QDrag(self)
                    drag.setMimeData(mime_data)

                    # Set the drag pixmap (you can create a custom pixmap if needed)
                    drag.setPixmap(QtGui.QPixmap.fromImage(QtGui.QImage("your_icon.png")))

                    # Use exec_ to specify the drag action (CopyAction for copying)
                    result = drag.exec(Qt.DropAction.CopyAction)

                    if result == Qt.DropAction.CopyAction:
                        print("File copied")
                    else:
                        print("File not copied")
        except Exception as e:
            logger.error(f'start_drag() = {e}')

class FolderSelectDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Music Folder")

        self.layout = QVBoxLayout()
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.open_folder_dialog)
        self.layout.addWidget(self.folder_button)
        self.setLayout(self.layout)

        self.selected_folder = None

    def open_folder_dialog(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Music Folder", os.path.expanduser("~"))
            if folder:
                self.selected_folder = folder
                self.accept()
        except Exception as e:
            logger.error(f'open_folder_dialog() = {e}')


if __name__ == "__main__":
    try:
        import sys
        sys.coinit_flags = 2
        app = QApplication(sys.argv)
        ui = Ui()
        ui.show()
        sleep(0.5)
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f'MAIN LOOP = {e}')



