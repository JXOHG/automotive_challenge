import { useState, useEffect, useRef } from "react";
import { 
  Upload, 
  ImageIcon, 
  RefreshCw, 
  AlertCircle, 
  Video, 
  CameraOff 
} from "lucide-react";

const API_BASE_URL = "http://192.168.137.135:5000/api";
const CAMERA_FEED_URL = "http://172.30.179.110:5001/video_feed";

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
  const [liveResults, setLiveResults] = useState(null);
  const [streamSrc, setStreamSrc] = useState(null);

  const videoRef = useRef(null);
  const abortControllerRef = useRef(new AbortController());
  const streamAbortControllerRef = useRef(null);
  const streamReaderRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const checkHealth = async (retries = 3, delay = 2000) => {
      for (let i = 0; i < retries; i++) {
        try {
          const response = await fetch(`${API_BASE_URL}/health`, { timeout: 5000 });
          console.log(`Health check attempt ${i + 1}: Status ${response.status}`);
          if (response.ok) {
            setApiHealthy(true);
            return;
          } else {
            console.warn(`Health check failed with status: ${response.status}`);
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

  useEffect(() => {
    if (liveMode) {
      startVideoFeed();
    } else {
      stopVideoFeed();
    }
    return () => stopVideoFeed();
  }, [liveMode]);

  const startVideoFeed = () => {
    setStreamSrc(CAMERA_FEED_URL);
    streamAbortControllerRef.current = new AbortController();

    fetch(CAMERA_FEED_URL, { 
      method: "GET",
      signal: streamAbortControllerRef.current.signal
    })
      .then(response => {
        const reader = response.body.getReader();
        streamReaderRef.current = reader;
        let chunks = "";

        const processStream = ({ done, value }) => {
          if (done || !liveMode) {
            reader.cancel();
            return;
          }

          chunks += new TextDecoder().decode(value);
          const parts = chunks.split("--frame");
          chunks = parts.pop();

          parts.forEach(part => {
            const dataMatch = part.match(/data: ({.*?})\r\n\r\n/s);
            if (dataMatch) {
              try {
                const data = JSON.parse(dataMatch[1]);
                if (data.total_spots !== undefined) {
                  setLiveResults({
                    total_spots: data.total_spots || 0,
                    empty_spots: data.empty_spots || 0,
                    filled_spots: data.filled_spots || 0
                  });
                }
              } catch (error) {
                console.error("Error parsing results:", error);
              }
            }
          });

          if (liveMode) {
            reader.read().then(processStream);
          }
        };

        reader.read().then(processStream);
      })
      .catch(error => {
        if (error.name !== "AbortError") {
          console.error("Stream failed:", error);
          setLiveMode(false);
        }
      });
  };

  const stopVideoFeed = () => {
    setStreamSrc(null);
    setLiveResults(null);

    if (streamAbortControllerRef.current) {
      streamAbortControllerRef.current.abort();
    }
    if (streamReaderRef.current) {
      streamReaderRef.current.cancel();
      streamReaderRef.current = null;
    }
    streamAbortControllerRef.current = null;
  };

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
      });
    } catch (error) {
      setError(error.message || "Analysis failed");
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

  const handleSelectImageClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="upload-container">
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

      {liveMode ? (
        <div className="live-feed-container">
          <div className="live-feed-card">
            <img
              ref={videoRef}
              src={streamSrc}
              alt="Live Feed"
              className="live-video"
              onLoad={() => console.log("Stream image loaded")}
              onError={(e) => {
                console.error("Image load failed:", e);
                setLiveMode(false);
              }}
            />
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
                <div className="spot-map">
                  {Array.from({ length: liveResults.total_spots }).map((_, index) => (
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
                  <span>Updates every ~10 seconds</span>
                </div>
              </div>
            ) : (
              <div className="feed-loading">
                <RefreshCw className="animate-spin" />
                <span>Analyzing first frame...</span>
              </div>
            )}
          </div>
        </div>
      ) : (
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
                <img src={image} alt="Uploaded preview" className="preview-image" />
                <div className="preview-actions">
                  <button onClick={resetAnalysis} className="secondary-button">
                    Upload New Image
                  </button>
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