import { useState } from "react"
import { Upload, ImageIcon, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'

// Real API functions to interact with Flask backend
const API_BASE_URL = "http://localhost:5000/api" // Change this to your Raspberry Pi's address

// Function to send image to API for analysis
async function analyzeImage(imageFile, locationId = "default") {
  console.log("Sending image to API:", imageFile.name)
  
  // Create a FormData object to send the file
  const formData = new FormData()
  formData.append('file', imageFile)
  formData.append('location_id', locationId)
  
  try {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: 'POST',
      body: formData,
      // No Content-Type header - fetch sets it automatically with boundary for FormData
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || "API request failed")
    }
    
    const data = await response.json()
    return {
      success: true,
      data: {
        totalSpots: data.total_spots,
        availableSpots: data.empty_spots,
        occupiedSpots: data.filled_spots,
        confidence: data.occupancy_rate, // Using occupancy rate as confidence for now
        processingTime: 1.2, // Could add processing time to API response
        // Convert the spots_status array to a spotMap array of booleans
        spotMap: data.spots_status.map(spot => spot.status === 'filled')
      }
    }
  } catch (error) {
    console.error("API error:", error)
    throw error
  }
}

// Function to get current parking status
async function getParkingStatus(locationId = "default") {
  try {
    const response = await fetch(`${API_BASE_URL}/parking_status?location_id=${locationId}`)
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || "Failed to get parking status")
    }
    
    return await response.json()
  } catch (error) {
    console.error("Failed to fetch parking status:", error)
    throw error
  }
}

// Check API health
async function checkApiHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    return response.ok
  } catch (error) {
    console.error("API health check failed:", error)
    return false
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
  const [apiHealthy, setApiHealthy] = useState(null) // null (unknown), true, or false

  // Check API health on component mount
  useState(() => {
    const checkHealth = async () => {
      const isHealthy = await checkApiHealth()
      setApiHealthy(isHealthy)
    }
    checkHealth()
  }, [])

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
    
    // Simulate progress for better UX (since we can't get real-time progress from the API)
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
      // Call real API with the image file
      const response = await analyzeImage(file)
      
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
      {apiHealthy === false && (
        <div className="api-warning">
          <AlertCircle className="warning-icon" />
          <span>API server is not responding. Check your connection to the Raspberry Pi.</span>
        </div>
      )}
      
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
                  disabled={isAnalyzing || apiHealthy === false}
                  className="primary-button"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="button-icon animate-spin" />
                      {apiStatus === 'sending' ? 'Sending to Raspberry Pi...' : 
                       apiStatus === 'processing' ? 'Processing with CNN...' : 
                       'Completing analysis...'}
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
                      {apiStatus === 'sending' ? 'Sending image to Raspberry Pi...' : 
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
                    <p className="error-help">Please try again or check if the Raspberry Pi is online.</p>
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