import { useState, useEffect, useRef } from "react";
import { 
  Upload, 
  ImageIcon, 
  RefreshCw, 
  AlertCircle, 
  Video, 
  CameraOff,
  Eye,
  EyeOff
} from "lucide-react";

const API_BASE_URL = "http://192.168.137.135:5000/api"; // Backend API
const SIMULATOR_BASE_URL = "http://172.30.179.110:5001"; // Simulator
const ANALYSIS_POLL_INTERVAL = 5000; // 5 seconds

function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function ParkingAnalyzer() {
  const [showOverlay, setShowOverlay] = useState(true);
  const [image, setImage] = useState(null);
  const [file, setFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [apiHealthy, setApiHealthy] = useState(null);
  const [liveMode, setLiveMode] = useState(false);
  const [liveResults, setLiveResults] = useState(null);
  const [isStreamLoaded, setIsStreamLoaded] = useState(false);

  const videoRef = useRef(null);
  const abortControllerRef = useRef(new AbortController());
  const pollIntervalRef = useRef(null);
  const fileInputRef = useRef(null);

  // Check API health on component mount
  useEffect(() => {
    const checkHealth = async (retries = 3, delay = 2000) => {
      for (let i = 0; i < retries; i++) {
        try {
          const response = await fetch(`${API_BASE_URL}/health`, { timeout: 5000 });
          if (response.ok) {
            setApiHealthy(true);
            return;
          }
        } catch (error) {
          console.error(`Health check attempt ${i + 1} failed: ${error.message}`);
        }
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
      setApiHealthy(false);
    };
    checkHealth();
  }, []);

  // Handle live mode toggling
  useEffect(() => {
    if (liveMode) {
      startLiveMode();
    } else {
      stopLiveMode();
    }
    return () => stopLiveMode();
  }, [liveMode]);

  // Update video feed URL when showOverlay changes in live mode
  useEffect(() => {
    if (liveMode && videoRef.current) {
      videoRef.current.src = `${SIMULATOR_BASE_URL}/video_feed?showOverlay=${showOverlay}`;
    }
  }, [showOverlay, liveMode]);

  // Start live mode polling for analysis results
  const startLiveMode = () => {
    setIsStreamLoaded(false);
    
    // Start polling for analysis results from /current_analysis
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(`${SIMULATOR_BASE_URL}/current_analysis`);
        if (!response.ok) throw new Error("Failed to fetch analysis");
        
        const data = await response.json();
        if (data && Object.keys(data).length > 0) {
          setLiveResults({
            total_spots: data.total_spots || 0,
            empty_spots: data.empty_spots || 0,
            filled_spots: data.filled_spots || 0,
            timestamp: data.timestamp || new Date().toISOString(),
            occupancy_rate: data.occupancy_rate || 0
          });
        }
      } catch (error) {
        console.error("Error polling for results:", error);
      }
    }, ANALYSIS_POLL_INTERVAL);
  };

  // Stop live mode and clean up
  const stopLiveMode = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setLiveResults(null);
    setIsStreamLoaded(false);
  };

  // Handle image analysis
  async function analyzeImage(imageFile) {
    const formData = new FormData();
    formData.append("file", imageFile);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        body: formData,
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error("Analysis failed");
      return await response.json();
    } catch (error) {
      if (error.name !== "AbortError") throw error;
    }
  }

  // Handle image upload from file input
  const handleImageUpload = (e) => {
    setLiveMode(false);
    const file = e.target.files?.[0];
    if (!file) return;

    setFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setImage(e.target.result);
    reader.readAsDataURL(file);
    setResults(null);
    setError(null);
  };

  // Handle analyze button click
  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setError(null);
  
    try {
      const data = await analyzeImage(file);
      setResults({
        totalSpots: data.total_spots,
        availableSpots: data.empty_spots,
        occupiedSpots: data.filled_spots,
        spotMap: data.spots_status?.map(spot => spot.status === "filled") || [],
        overlayImage: data.overlay_image ? `data:image/jpeg;base64,${data.overlay_image}` : null
      });
    } catch (error) {
      setError(error.message || "Analysis failed");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reset analysis state
  const resetAnalysis = () => {
    setImage(null);
    setFile(null);
    setResults(null);
    setError(null);
  };

  // Handle select image button click
  const handleSelectImageClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="upload-container">
      {/* API Health Status */}
      {apiHealthy === null && (
        <div className="api-warning">
          <RefreshCw className="animate-spin warning-icon" />
          <span>Checking backend API status...</span>
        </div>
      )}
      {apiHealthy === false && (
        <div className="api-warning">
          <AlertCircle className="warning-icon" />
          <span>Backend API is unavailable. Check Raspberry Pi connection.</span>
        </div>
      )}

      {/* Controls */}
      <div className="simulation-controls">
        <button
          onClick={() => setLiveMode(!liveMode)}
          className={cn("control-button", liveMode && "active")}
          disabled={apiHealthy === false}
        >
          {liveMode ? <CameraOff size={18} /> : <Video size={18} />}
          {liveMode ? "Stop Live Feed" : "Start Live Feed"}
        </button>
      </div>

      {/* Live Feed Section */}
      {liveMode ? (
        <div className="live-feed-container">
          <div className="live-feed-card">
            {/* The video feed */}
            <div className="video-container">
              <img
                ref={videoRef}
                src={`${SIMULATOR_BASE_URL}/video_feed?showOverlay=${showOverlay}`}
                alt="Live Feed"
                className={cn("live-video", isStreamLoaded ? "loaded" : "loading")}
                onLoad={() => setIsStreamLoaded(true)}
                onError={(e) => {
                  console.error("Stream error:", e);
                  setLiveMode(false);
                }}
              />
              
              {!isStreamLoaded && (
                <div className="stream-loading">
                  <RefreshCw className="animate-spin" />
                  <span>Loading video stream...</span>
                </div>
              )}
            </div>
            
            {/* Overlay toggle and live results */}
            <div className="live-controls">
              <button 
                onClick={() => setShowOverlay(!showOverlay)} 
                className="toggle-button"
              >
                {showOverlay ? (
                  <>
                    <EyeOff size={16} />
                    Hide Overlay
                  </>
                ) : (
                  <>
                    <Eye size={16} />
                    Show Overlay
                  </>
                )}
              </button>
            </div>
            
            {liveResults ? (
              <div className="live-results-overlay">
                <div className="stats-panel">
                  <div className="stat-item total">
                    <span className="stat-label">Total Spots</span>
                    <span className="stat-value">{liveResults.total_spots}</span>
                  </div>
                  <div className="stat-item available">
                    <span className="stat-label">Available</span>
                    <span className="stat-value">{liveResults.empty_spots}</span>
                  </div>
                  <div className="stat-item occupied">
                    <span className="stat-label">Occupied</span>
                    <span className="stat-value">{liveResults.filled_spots}</span>
                  </div>
                </div>
                <div className="occupancy-meter">
                  <div 
                    className="occupancy-fill" 
                    style={{ width: `${liveResults.occupancy_rate || 0}%` }}
                  />
                  <span className="occupancy-text">
                    {Math.round(liveResults.occupancy_rate || 0)}% Occupied
                  </span>
                </div>
                <div className="spot-map">
                  {Array.from({ length: liveResults.total_spots || 0 }).map((_, index) => (
                    <div
                      key={index}
                      className={cn(
                        "spot-marker",
                        index < liveResults.filled_spots ? "occupied" : "available"
                      )}
                    />
                  ))}
                </div>
                <div className="live-note">
                  <span>Last updated: {liveResults.timestamp || 'Processing...'}</span>
                </div>
              </div>
            ) : (
              <div className="feed-loading">
                <RefreshCw className="animate-spin" />
                <span>Waiting for analysis data...</span>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Image Upload Section */
        <div className="upload-section">
          {!image ? (
            <div className="upload-card">
              <label className="upload-label">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden-input"
                />
                <div className="upload-content">
                  <ImageIcon className="upload-icon" />
                  <span className="upload-title">Analyze Parking Lot</span>
                  <span className="upload-subtitle">
                    Upload an image or start the live feed
                  </span>
                  <button
                    onClick={handleSelectImageClick}
                    className="upload-button"
                  >
                    <Upload className="button-icon" />
                    Select Image
                  </button>
                  <span className="file-types">JPEG, PNG up to 100MB</span>
                </div>
              </label>
            </div>
          ) : (
            <div className="analysis-section">
              <div className="image-preview-card">
                <img 
                  src={showOverlay && results?.overlayImage ? results.overlayImage : image} 
                  alt="Uploaded preview" 
                  className="preview-image" 
                />
                <div className="preview-actions">
                  <button onClick={resetAnalysis} className="secondary-button">
                    Upload New Image
                  </button>
                  {results && results.overlayImage && (
                    <button 
                      onClick={() => setShowOverlay(!showOverlay)} 
                      className="toggle-button"
                    >
                      {showOverlay ? (
                        <>
                          <EyeOff size={16} />
                          Hide Overlay
                        </>
                      ) : (
                        <>
                          <Eye size={16} />
                          Show Overlay
                        </>
                      )}
                    </button>
                  )}
                  <button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || apiHealthy === false}
                    className="primary-button"
                  >
                    {isAnalyzing ? (
                      <>
                        <RefreshCw className="animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      "Analyze Image"
                    )}
                  </button>
                </div>
              </div>

              {/* Analysis Results */}
              {(results || error) && (
                <div className="analysis-results">
                  {error ? (
                    <div className="error-message">
                      <AlertCircle className="error-icon" />
                      {error}
                    </div>
                  ) : (
                    <>
                      <div className="results-summary">
                        <div className="summary-item total">
                          <span>Total Spots</span>
                          <strong>{results.totalSpots}</strong>
                        </div>
                        <div className="summary-item available">
                          <span>Available</span>
                          <strong>{results.availableSpots}</strong>
                        </div>
                        <div className="summary-item occupied">
                          <span>Occupied</span>
                          <strong>{results.occupiedSpots}</strong>
                        </div>
                      </div>
                      <div className="spot-visualization">
                        {results.spotMap.map((occupied, index) => (
                          <div
                            key={index}
                            className={cn(
                              "spot-box",
                              occupied ? "occupied" : "available"
                            )}
                          >
                            <span>{index + 1}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}