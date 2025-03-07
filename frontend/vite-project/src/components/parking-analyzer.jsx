import { useState } from "react"
import { Upload, ImageIcon, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'

// Mock API function to simulate sending image to backend
async function mockApiCall(imageFile) {
  console.log("Sending image to mock API:", imageFile.name)
  
  // Create a FormData object (this is how you'd normally send files to an API)
  const formData = new FormData()
  formData.append('image', imageFile)
  
  // Simulate network delay (1-3 seconds)
  const delay = 1000 + Math.random() * 2000
  await new Promise(resolve => setTimeout(resolve, delay))
  
  // 10% chance of API error to test error handling
  if (Math.random() < 0.1) {
    throw new Error("API connection error")
  }
  
  // Generate mock results as if they came from a CNN model
  const totalSpots = Math.floor(Math.random() * 20) + 10 // 10-30 spots
  const occupiedSpots = Math.floor(Math.random() * totalSpots)
  const availableSpots = totalSpots - occupiedSpots
  
  // Generate a random map of occupied/available spots
  const spotMap = Array(totalSpots).fill(false).map(() => Math.random() > 0.5)
  
  // Return mock API response
  return {
    success: true,
    data: {
      totalSpots,
      availableSpots,
      occupiedSpots,
      spotMap,
      confidence: Math.round(85 + Math.random() * 10), // 85-95% confidence
      processingTime: Math.round(delay / 100) / 10 // Processing time in seconds
    }
  }
}

// Utility function to combine class names
function cn(...classes) {
  return classes.filter(Boolean).join(" ")
}

export function ParkingAnalyzer() {
  const [image, setImage] = useState(null)
  const [file, setFile] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const [apiStatus, setApiStatus] = useState(null) // 'sending', 'processing', 'complete', 'error'

  const handleImageUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      
      const reader = new FileReader()
      reader.onload = (event) => {
        setImage(event.target?.result)
        setResults(null) // Reset results when new image is uploaded
        setError(null)
        setApiStatus(null)
      }
      reader.readAsDataURL(selectedFile)
    }
  }

  const handleAnalyze = async () => {
    if (!file) return
    
    setIsAnalyzing(true)
    setProgress(0)
    setError(null)
    setApiStatus('sending')
    
    // Simulate progress updates
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev < 30) {
          // Slow progress during "sending" phase
          return prev + Math.random() * 5
        } else if (prev < 90) {
          // Faster progress during "processing" phase
          setApiStatus('processing')
          return prev + Math.random() * 10
        } else {
          // Slow down as we approach completion
          return prev + Math.random() * 2
        }
      })
    }, 300)
    
    try {
      // Call mock API
      const response = await mockApiCall(file)
      
      // Update progress to 100%
      setProgress(100)
      setApiStatus('complete')
      
      // Set results from API response
      setResults(response.data)
    } catch (error) {
      console.error("Error analyzing image:", error)
      setError(error.message || "Failed to analyze image")
      setApiStatus('error')
    } finally {
      clearInterval(progressInterval)
      setTimeout(() => {
        setIsAnalyzing(false)
      }, 500) // Keep progress bar at 100% for a moment
    }
  }

  const resetAnalysis = () => {
    setImage(null)
    setFile(null)
    setResults(null)
    setError(null)
    setApiStatus(null)
  }

  return (
    <div className="upload-container">
      {!image ? (
        <div className="upload-box">
          <div className="upload-content">
            <ImageIcon className="upload-icon" />
            <div className="upload-text">
              <label htmlFor="image-upload" className="upload-label">
                <span className="upload-message">
                  Upload a parking lot image
                </span>
                <button className="upload-button">
                  <Upload className="button-icon" />
                  Select Image
                </button>
                <input
                  id="image-upload"
                  name="image-upload"
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  onChange={handleImageUpload}
                />
              </label>
              <p className="upload-info">
                PNG, JPG, GIF up to 10MB
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="analysis-container">
          <div className="image-preview-container">
            <div className="image-preview-card">
              <div className="image-preview">
                <img src={image || "/placeholder.svg"} alt="Parking lot" className="preview-image" />
              </div>
              <div className="preview-actions">
                <button onClick={resetAnalysis} className="secondary-button">
                  Upload Different Image
                </button>
                <button 
                  onClick={handleAnalyze} 
                  disabled={isAnalyzing}
                  className="primary-button"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="button-icon animate-spin" />
                      {apiStatus === 'sending' ? 'Sending...' : 
                       apiStatus === 'processing' ? 'Processing...' : 
                       'Completing...'}
                    </>
                  ) : (
                    'Analyze Image'
                  )}
                </button>
              </div>
            </div>
            
            {(isAnalyzing || results || error) && (
              <div className="results-card">
                <h3 className="results-title">Analysis Results</h3>
                
                {isAnalyzing && (
                  <div className="analysis-progress">
                    <div className="status-message">
                      {apiStatus === 'sending' ? 'Sending image to API...' : 
                       apiStatus === 'processing' ? 'Processing image through CNN model...' : 
                       'Finalizing results...'}
                    </div>
                    <div className="progress-container">
                      <div 
                        className="progress-bar" 
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                
                {error && (
                  <div className="error-container">
                    <AlertCircle className="error-icon" />
                    <div className="error-message">{error}</div>
                    <p className="error-help">Please try again or use a different image.</p>
                  </div>
                )}
                
                {results && (
                  <div className="results-content">
                    <div className="api-info">
                      <div className="api-status">
                        <CheckCircle className="success-icon" />
                        <span>Analysis complete</span>
                      </div>
                      <div className="api-details">
                        <span>Confidence: {results.confidence}%</span>
                        <span>Processing time: {results.processingTime}s</span>
                      </div>
                    </div>
                    
                    <div className="stats-container">
                      <div className="stat-card total">
                        <div className="stat-label">Total Spots</div>
                        <div className="stat-value">{results.totalSpots}</div>
                      </div>
                      <div className="stat-card available">
                        <div className="stat-label">Available</div>
                        <div className="stat-value">{results.availableSpots}</div>
                      </div>
                      <div className="stat-card occupied">
                        <div className="stat-label">Occupied</div>
                        <div className="stat-value">{results.occupiedSpots}</div>
                      </div>
                    </div>
                    
                    <div className="spot-map-container">
                      <h4 className="spot-map-title">Parking Spot Map</h4>
                      <div className="spot-map">
                        {results.spotMap.map((isOccupied, index) => (
                          <div
                            key={index}
                            className={`spot-indicator ${isOccupied ? 'occupied' : 'available'}`}
                          >
                            {index + 1}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
