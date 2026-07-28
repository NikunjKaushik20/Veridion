import { StrictMode, useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { App } from "./App";
import { Dashboard } from "./Dashboard";

function Root() {
  const [route, setRoute] = useState(window.location.pathname);

  useEffect(() => {
    const handlePopState = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  if (route === "/dashboard") {
    return (
      <Dashboard
        onBack={() => {
          window.history.pushState({}, "", "/");
          setRoute("/");
        }}
      />
    );
  }

  return (
    <App
      onEnter={() => {
        window.history.pushState({}, "", "/dashboard");
        setRoute("/dashboard");
      }}
    />
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
