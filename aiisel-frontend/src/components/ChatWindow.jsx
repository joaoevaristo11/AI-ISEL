import React, { useState, useRef, useEffect } from "react";
import "./ChatWindow.css";

export default function ChatWindow({ isOpen }) {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "👋 Olá! Como posso ajudar?" },
  ]);

  const [inputValue, setInputValue] = useState("");

  const messagesEndRef = useRef(null);

  // ✅ Todos os hooks são sempre chamados, independentemente do isOpen
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 🔽 só aqui verificamos o isOpen
  if (!isOpen) return null;

  const handleSendMessage = () => {
    const trimmedInput = inputValue.trim();
    if (!trimmedInput) return;

    setMessages((prev) => [...prev, { sender: "user", text: trimmedInput }]);
    setInputValue("");
  };

  const handleEnter = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-header">ISEL ChatBot 🤖</div>

      <div className="chat-body">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.sender === "user" ? "user" : "bot"}`}
          >
            {msg.text}
          </div>
        ))}

        <div ref={messagesEndRef} /> {/* 🔽 Elemento invisível para scroll */}
      </div>

      <div className="chat-input">
        <input
          type="text"
          placeholder="Escreva aqui..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleEnter}
        />
        <button onClick={handleSendMessage}>➤</button>
      </div>
    </div>
  );
}
