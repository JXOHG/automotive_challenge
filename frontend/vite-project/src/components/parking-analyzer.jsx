import { useState, useEffect } from "react";
import { Upload, ImageIcon, RefreshCw, CheckCircle, AlertCircle, Video, CameraOff } from "lucide-react";

const API_BASE_URL = "http://192.168.2.32:5000/api";
const SAMPLE_IMAGES = [
  "parking1.jpg",
  "parking2.jpg",
  "parking3.jpg",
  "parking4.jpg",
  "parking5.jpg",
];

async function analyzeImage(imageFile, locationId = "default") {
  console.log("Starting API call to Flask backend...");
  const formData = new FormData();
  formData.append("file", imageFile);
  formData.append("location_id", locationId);

  try {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "API request failed");
    }

    const data = await response.json();
    return {
      success: true,
      data: {
        totalSpots: data.total_spots,
        availableSpots: data.empty_spots,
        occupiedSpots: data.filled_spots,
        confidence: data.occupancy_rate,
        spotMap: data.spots_status.map((spot) => spot.status === "filled"),
      },
    };
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
}

async function checkApiHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch (error) {
    return false;
  }
}

function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function ParkingAnalyzer() {
  const [image, setImage] = useState(null);
  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [apiStatus, setApiStatus] = useState(null);
  const [apiHealthy, setApiHealthy] = useState(null);
  const [liveMode, setLiveMode] = useState(false);
  const [currentSampleIndex, setCurrentSampleIndex] = useState(0);

  useEffect(() => {
    const checkHealth = async () => {
      const isHealthy = await checkApiHealth();
      setApiHealthy(isHealthy);
    };
    checkHealth();
  }, []);

  useEffect(() => {
    let interval;
    if (liveMode && apiHealthy) {
      interval = setInterval(() => {
        const nextIndex = (currentSampleIndex + 1) % SAMPLE_IMAGES.length;
        setCurrentSampleIndex(nextIndex);

        fetch(SAMPLE_IMAGES[nextIndex])
          .then((res) => res.blob())
          .then((blob) => {
            const simulatedFile = new File([blob], `sample_${nextIndex}.jpg`, {
              type: "image/jpeg",
            });
            handleAutoAnalyze(simulatedFile);
          });
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [liveMode, currentSampleIndex, apiHealthy]);

  const handleAutoAnalyze = async (simulatedFile) => {
    try {
      const response = await analyzeImage(simulatedFile);
      setResults(response.data);
      setError(null);
    } catch (error) {
      console.error("Simulation error:", error);
    }
  };

  const handleImageUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);

      const reader = new FileReader();
      reader.onload = (event) => {
        setImage(event.target?.result);
        setResults(null);
        setError(null);
        setApiStatus(null);
      };
      reader.readAsDataURL(selectedFile);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;

    console.log("Starting analysis with file:", file.name);
    setIsAnalyzing(true);
    setProgress(0);
    setError(null);
    setApiStatus("sending");

    let progress = 0;
    const progressInterval = setInterval(() => {
      progress = Math.min(progress + 10, 90);
      setProgress(progress);
    }, 500);

    try {
      const response = await analyzeImage(file);
      setProgress(100);
      setApiStatus("complete");
      setResults(response.data);
    } catch (error) {
      console.error("Error in handleAnalyze:", error);
      setError(error.message || "Failed to analyze image");
      setApiStatus("error");
    } finally {
      clearInterval(progressInterval);
      setTimeout(() => {
        setIsAnalyzing(false);
      }, 500);
    }
  };

  const resetAnalysis = () => {
    setImage(null);
    setFile(null);
    setResults(null);
    setError(null);
    setApiStatus(null);
  };

  return (
    <div className="upload-container">
      {apiHealthy === false && (
        <div className="api-warning">
          <AlertCircle className="warning-icon" />
          <span>API server is not responding. Check your connection to the Raspberry Pi.</span>
        </div>
      )}

      <div className="simulation-controls">
        <button
          onClick={() => setLiveMode(!liveMode)}
          className={cn("simulation-button", liveMode && "active")}
        >
          {liveMode ? <CameraOff size={18} /> : <Video size={18} />}
          {liveMode ? " Stop Simulation" : " Start Live Simulation"}
        </button>
        <span className="simulation-status">
          {liveMode && `Sample ${currentSampleIndex + 1}/${SAMPLE_IMAGES.length}`}
        </span>
      </div>

      {!liveMode && (
        <>
          {!image ? (
            <div className="upload-box">
              <div className="upload-content">
                <ImageIcon className="upload-icon" />
                <div className="upload-text">
                  <label htmlFor="image-upload" className="upload-label">
                    <span className="upload-message">Upload a parking lot image</span>
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
                  <p className="upload-info">PNG, JPG, GIF up to 10MB</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="analysis-container">
              <div className="image-preview-container">
                <div className="image-preview-card">
                  <div className="image-preview">
                    <img src={image} alt="Parking lot" className="preview-image" />
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
                          {apiStatus === "sending"
                            ? "Sending to Raspberry Pi..."
                            : apiStatus === "processing"
                            ? "Processing with CNN..."
                            : "Completing analysis..."}
                        </>
                      ) : (
                        "Analyze Image"
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
                          {apiStatus === "sending"
                            ? "Sending image to Raspberry Pi..."
                            : apiStatus === "processing"
                            ? "Processing image through CNN model..."
                            : "Finalizing results..."}
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
                        <p className="error-help">
                          Please try again or check if the Raspberry Pi is online.
                        </p>
                      </div>
                    )}

                    {results && (
                      <div className="results-content">
                        <div className="api-info">
                          <CheckCircle className="success-icon" />
                          <span>Analysis complete</span>
                          <div className="api-details">
                            <span>Confidence: {results.confidence}%</span>
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
                                className={cn(
                                  "spot-indicator",
                                  isOccupied ? "occupied" : "available"
                                )}
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
        </>
      )}

      {liveMode && (
        <div className="simulation-view">
          <h3>Live Simulation Preview</h3>
          {results ? (
            <div className="live-results">
              <div className="live-preview">
                <img
                  src={SAMPLE_IMAGES[currentSampleIndex]}
                  alt="Live simulation"
                  className="simulation-image"
                />
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
            </div>
          ) : (
            <div className="simulation-loading">
              <RefreshCw className="animate-spin" />
              <span>Initializing live simulation...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}