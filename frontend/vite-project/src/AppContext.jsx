import { createContext, useContext, useState } from 'react';

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