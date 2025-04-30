import { useState } from 'react'
import axios from 'axios'
import { useDropzone } from 'react-dropzone'
import './App.css';


interface DetectionResult {
  video_url: string
  counts: number[]
}

export default function App() {
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'video/*': ['.mp4', '.mov']
    },
    multiple: false,
    onDrop: async (files) => {
      if (files.length === 0) return
      await processVideo(files[0])
    }
  })

  const processVideo = async (file: File) => {
    try {
      setLoading(true)
      setProgress(0)
      
      const formData = new FormData()
      formData.append('video', file)

      const { data } = await axios.post<DetectionResult>(
        'http://localhost:5000/process',
        formData,
        {
          onUploadProgress: (progressEvent) => {
            const percent = Math.round(
              (progressEvent.loaded * 100) / (progressEvent.total || 1)
            )
            setProgress(percent)
          },
          responseType: 'json'
        }
      )

      setResult(data)
    } catch (error) {
      console.error("Детали ошибки:", error.response?.data || error.message);
      alert("Ошибка: " + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>Детекция телевизоров в видео</h1>
      
      <div 
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''}`}
      >
        <input {...getInputProps()} />
        {loading ? (
          <div className="progress">
            <div 
              className="progress-bar" 
              style={{ width: `${progress}%` }}
            >
              {progress}%
            </div>
          </div>
        ) : (
          <p>Перетащите видео файл или кликните для выбора</p>
        )}
      </div>

      {result && (
        <div className="result">
          <h2>Результат обработки</h2>
          
          <div className="video-container">
            <video 
              controls 
              src={`http://localhost:5000${result.video_url}`}
            />
          </div>

          <div className="stats">
            <h3>Статистика</h3>
            <p>Максимум в кадре: {Math.max(...result.counts)}</p>
            <p>Среднее значение: {(result.counts.reduce((a, b) => a + b, 0) / result.counts.length).toFixed(1)}</p>
          </div>
        </div>
      )}
    </div>
  )
}