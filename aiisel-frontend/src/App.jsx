import React, { useState } from "react";
import ChatButton from "./components/ChatButton";
import ChatWindow from "./components/ChatWindow";
import "./App.css";

export default function App() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="App">
      <ChatButton onClick={() => setIsOpen(o => !o)} isOpen={isOpen} />
      <ChatWindow isOpen={isOpen} />   {/* SEM && */}
    </div>
  );
}
