import { useState, useEffect, useRef } from "react";
import { 
  Upload, 
  ImageIcon, 
  RefreshCw, 
  AlertCircle, 
  Video, 
  CameraOff 
} from "lucide-react";

const API_BASE_URL = "http://192.168.2.32:5000/api";
const SIMULATION_VIDEO = "/videos/parking-simulation.mp4";

async function analyzeImage(imageFile, locationId = "default", signal) {
  console.log("Starting API call to Flask backend...");
  const formData = new FormData();
  formData.append("file", imageFile);
  formData.append("location_id", locationId);

  try {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      body: formData,
      signal,
    });

    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      const text = await response.text();
      throw new Error(`Invalid response: ${text.slice(0, 100)}`);
    }

    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || `API request failed with status ${response.status}`);
    }

    return {
      success: true,
      data: {
        totalSpots: data.total_spots,
        availableSpots: data.empty_spots,
        occupiedSpots: data.filled_spots,
        confidence: data.occupancy_rate,
        spotMap: data.spots_status?.map((spot) => spot.status === "filled") || [],
      },
    };
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('Request aborted');
      return;
    }
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
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [apiHealthy, setApiHealthy] = useState(null);
  const [liveMode, setLiveMode] = useState(false);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const abortControllerRef = useRef(new AbortController());

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const isHealthy = await checkApiHealth();
        setApiHealthy(isHealthy);
      } catch (error) {
        setApiHealthy(false);
      }
    };
    checkHealth();
  }, []);

  useEffect(() => {
    if (liveMode) {
      startVideoProcessing();
    } else {
      stopVideoProcessing();
    }
    
    return () => stopVideoProcessing();
  }, [liveMode]);

  const startVideoProcessing = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    video.addEventListener('play', () => {
      const processFrame = async () => {
        if (video.paused || video.ended) return;

        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob(async (blob) => {
          const frameFile = new File([blob], `frame_${Date.now()}.jpg`, {
            type: 'image/jpeg',
          });
          
          try {
            const response = await analyzeImage(
              frameFile,
              "default",
              abortControllerRef.current.signal
            );
            if (response?.data) {
              setResults(response.data);
              setError(null);
            }
          } catch (error) {
            if (error.name !== 'AbortError') {
              console.error("Frame analysis error:", error);
            }
          }
        }, 'image/jpeg');

        animationFrameRef.current = requestAnimationFrame(processFrame);
      };

      setTimeout(() => {
        animationFrameRef.current = requestAnimationFrame(processFrame);
      }, 1000);
    });

    video.play().catch(error => {
      console.error("Video play failed:", error);
      setLiveMode(false);
    });
  };

  const stopVideoProcessing = () => {
    abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    if (videoRef.current) videoRef.current.pause();
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  };

  const handleImageUpload = (e) => {
    setLiveMode(false);
    if (e.target.files?.[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);

      const reader = new FileReader();
      reader.onload = (event) => {
        setImage(event.target?.result);
        setResults(null);
        setError(null);
      };
      reader.readAsDataURL(selectedFile);
    }
  };

  const handleAnalyze = async () => {
    setLiveMode(false);
    if (!file) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const response = await analyzeImage(
        file,
        "default",
        abortControllerRef.current.signal
      );
      if (response?.data) {
        setResults(response.data);
      }
    } catch (error) {
      setError(error.message || "Failed to analyze image");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resetAnalysis = () => {
    setImage(null);
    setFile(null);
    setResults(null);
    setError(null);
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
      </div>

      {liveMode ? (
        <div className="video-simulation">
          <video
            ref={videoRef}
            src={SIMULATION_VIDEO}
            muted
            loop
            style={{ display: 'none' }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          
          {results ? (
            <div className="live-results">
              <div className="live-preview">
                <video
                  src={SIMULATION_VIDEO}
                  muted
                  loop
                  autoPlay
                  className="simulation-video"
                />
                <div className="overlay-spots">
                  {results.spotMap?.map((isOccupied, index) => (
                    <div
                      key={index}
                      className={cn(
                        "spot-indicator",
                        isOccupied ? "occupied" : "available"
                      )}
                      style={{
                        left: `${(index % 5) * 20 + 5}%`,
                        top: `${Math.floor(index / 5) * 15 + 20}%`
                      }}
                    >
                      {index + 1}
                    </div>
                  ))}
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
            </div>
          ) : (
            <div className="simulation-loading">
              <RefreshCw className="animate-spin" />
              <span>Initializing video simulation...</span>
            </div>
          )}
        </div>
      ) : (
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
                          Analyzing...
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
                    {error && (
                      <div className="error-container">
                        <AlertCircle className="error-icon" />
                        <div className="error-message">{error}</div>
                      </div>
                    )}

                    {results && (
                      <div className="results-content">
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
                            {results.spotMap?.map((isOccupied, index) => (
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
    </div>
  );
}