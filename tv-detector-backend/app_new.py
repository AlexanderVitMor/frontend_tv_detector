from flask import Flask, request, jsonify, send_from_directory
from ultralytics import YOLO
import cv2
import tempfile
import os
from flask_cors import CORS

import shutil

# Путь к папке временных файлов
TEMP_DIR = "./data/tv_data/temp_processing"

# Очистка папки перед запуском (опционально)
shutil.rmtree(TEMP_DIR, ignore_errors=True)
os.makedirs(TEMP_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)  # Разрешить запросы с любых доменов
model = YOLO('yolov8n.pt')  # Убедитесь, что модель загружается без ошибок

@app.route('/')
def home():
    return "TV Detection API is running! Use /process endpoint to upload video."

@app.route('/process', methods=['POST'])
def process_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video uploaded'}), 400

        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        # Сохраняем входное видео
        input_path = os.path.join(TEMP_DIR, "input_video.mp4")
        video_file.save(input_path)

        # Инициализация видео-потоков
        cap = cv2.VideoCapture(input_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Выходной файл
        output_filename = "output_video.mp4"
        output_path = os.path.join(TEMP_DIR, output_filename)

        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        counts = []

        # Обработка кадров
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                results = model(frame, classes=[62])
                count = len(results[0].boxes)
                counts.append(count)

                annotated_frame = results[0].plot()
                out.write(annotated_frame)
        finally:
            # Гарантированное освобождение ресурсов
            cap.release()
            out.release()

        # Удаление временных файлов (опционально)
        #os.remove(input_path)
        #os.remove(output_path)

        return jsonify({
            'video_url': f'/download/{output_filename}',
            'counts': counts
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(
        TEMP_DIR,
        filename,
        mimetype='video/mp4',  # Явно указываем MIME-тип
        as_attachment=False
    )

if __name__ == '__main__':
    app.run(debug=True)