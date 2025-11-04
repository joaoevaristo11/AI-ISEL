import React from "react";
import "./ChatWindow.css";

export default function ChatWindow({ isOpen }) {
  if (!isOpen) return null; 

  return (
    <div className="chat-window">
      <div className="chat-header">ISEL ChatBot 🤖</div>
      <div className="chat-body">
        <p>👋 Olá! Como posso ajudar?</p>
      </div>
      <div className="chat-input">
        <input type="text" placeholder="Escreva aqui..." />
        <button>➤</button>
      </div>
    </div>
  )
}
