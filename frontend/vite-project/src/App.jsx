import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { ParkingAnalyzer } from './components/parking-analyzer'
import { createContext, useContext, useState, useEffect } from 'react'
import './App.css'

// Create a context for app state management
const AppContext = createContext();

export function AppProvider({ children }) {
  const [shouldReset, setShouldReset] = useState(false);

  const resetApp = () => {
    setShouldReset(true);
    // Reset the flag after a short delay
    setTimeout(() => setShouldReset(false), 100);
  };

  return (
    <AppContext.Provider value={{ shouldReset, resetApp }}>
      {children}
    </AppContext.Provider>
  );
}

export const useAppContext = () => useContext(AppContext);

// Navbar component
function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { resetApp } = useAppContext();
  
  const handleLogoClick = () => {
    resetApp(); // Reset app state
    navigate('/'); // Navigate to home
  };
  
  return (
    <nav className="navbar">
      <div className="nav-container">
        <div 
          className="nav-brand" 
          onClick={handleLogoClick}
          style={{ cursor: 'pointer' }}
        >
          <span className="brand-text">Parking Analyzer</span>
        </div>
        <div className="nav-links">
          <Link
            to="/"
            className={`nav-link ${location.pathname === "/" ? "active" : ""}`}
          >
            Home
          </Link>
          <Link
            to="/about"
            className={`nav-link ${location.pathname === "/about" ? "active" : ""}`}
          >
            About
          </Link>
        </div>
      </div>
    </nav>
  );
}

// Home page component
function HomePage() {
  return (
    <main className="main-content">
      <div className="content-container">
        <div className="header">
          <h1>Parking Lot Analyzer</h1>
          <p className="subtitle">
            Upload an image of a parking lot to analyze available spaces
          </p>
        </div>
        
        <ParkingAnalyzer />
      </div>
    </main>
  );
}

// About page component
function AboutPage() {
  // Existing about page code
  return (
    <main className="main-content">
      <div className="content-container">
        <div className="header">
          <h1>About Parking Lot Analyzer</h1>
        </div>
        
        <div className="card">
          <h2>How It Works</h2>
          <p>
            The Parking Lot Analyzer uses a convolutional neural network (CNN) to analyze images of parking lots and determine which spaces are occupied and which are available.
          </p>
          
          <h2>Technology</h2>
          <p>
            Our system is built using:
          </p>
          <ul className="feature-list">
            <li>React and Vite for the frontend interface</li>
            <li>Convolutional Neural Networks for image analysis</li>
            <li>Computer vision techniques for parking space detection</li>
          </ul>
          
          <h2>Accuracy</h2>
          <p>
            The system has been trained on thousands of parking lot images and achieves an accuracy of over 95% in detecting available and occupied spaces under various lighting and weather conditions.
          </p>
        </div>
      </div>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <div className="app-wrapper">
          <Navbar />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </div>
      </AppProvider>
    </BrowserRouter>
  );
}

export default App