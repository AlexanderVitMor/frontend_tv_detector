from flask import Flask, request, jsonify, send_from_directory, Response
from ultralytics import YOLO
import cv2
import tempfile
import os
from flask_cors import CORS
import shutil
from typing import Dict, Any, List, Tuple

# Конфигурационные параметры
TEMP_DIR: str = "./data/tv_data/temp_processing"
ALLOWED_EXTENSIONS: Tuple[str, ...] = ('.mp4', '.mov', '.avi')
MODEL_PATH: str = 'yolov8n.pt'

app: Flask = Flask(__name__)
CORS(app)
model: YOLO = YOLO(MODEL_PATH)


def setup_temp_directory() -> None:
    """Инициализирует и очищает временную директорию для обработки файлов."""
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def validate_video_file(file) -> Tuple[bool, Dict[str, Any]]:
    """
    Валидирует загружаемый видеофайл.

    Args:
        file: Файловый объект из запроса

    Returns:
        Кортеж (валиден ли файл, сообщение об ошибке)
    """
    if not file:
        return False, {'error': 'No file uploaded'}
    if file.filename == '':
        return False, {'error': 'Empty filename'}
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        return False, {'error': 'Unsupported file format'}
    return True, {}


@app.route('/')
def home() -> str:
    """Возвращает статусное сообщение API."""
    return "TV Detection API is running! Use /process endpoint to upload video."


@app.route('/process', methods=['POST'])
def process_video() -> Tuple[Response, int]:
    """
    Обрабатывает загруженное видео, выполняя детекцию телевизоров.

    Формат запроса:
        POST /process
        Content-Type: multipart/form-data
        Body: video=[видеофайл]

    Формат ответа:
        {
            "video_url": "URL обработанного видео",
            "counts": [массив количества телевизоров в каждом кадре]
        }
    """
    try:
        # Валидация входящего файла
        is_valid, error = validate_video_file(request.files.get('video'))
        if not is_valid:
            return jsonify(error), 400

        video_file = request.files['video']

        # Сохранение временного файла
        input_path: str = os.path.join(TEMP_DIR, "input_video.mp4")
        video_file.save(input_path)

        # Инициализация видеопотоков
        cap: cv2.VideoCapture = cv2.VideoCapture(input_path)
        fps: int = int(cap.get(cv2.CAP_PROP_FPS))
        width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Настройка выходного файла
        output_filename: str = "output_video.mp4"
        output_path: str = os.path.join(TEMP_DIR, output_filename)
        fourcc: int = cv2.VideoWriter_fourcc(*'avc1')
        out: cv2.VideoWriter = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        counts: List[int] = []

        # Обработка кадров
        try:
            while cap.isOpened():
                ret: bool, frame = cap.read()
                if not ret:
                    break

                # Детекция объектов
                results = model(frame, classes=[62])
                count: int = len(results[0].boxes)
                counts.append(count)

                # Визуализация и запись кадра
                annotated_frame = results[0].plot()
                out.write(annotated_frame)
        finally:
            # Освобождение ресурсов
            cap.release()
            out.release()

        return jsonify({
            'video_url': f'/download/{output_filename}',
            'counts': counts
        }), 200

    except Exception as e:
        app.logger.error(f"Processing error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/download/<filename>')
def download_file(filename: str) -> Response:
    """
    Отдает обработанный видеофайл.

    Args:
        filename: Имя файла для скачивания

    Returns:
        Видеофайл в формате MP4
    """
    return send_from_directory(
        TEMP_DIR,
        filename,
        mimetype='video/mp4',
        as_attachment=False
    )


if __name__ == '__main__':
    setup_temp_directory()
    app.run(host='0.0.0.0', port=5000, debug=True)