import React, { useState } from "react";
import "./ChatWindow.css";

export default function ChatWindow({ isOpen }) {

  const [messages, setMessages] = useState([
    {sender: "bot", text:"👋 Olá! Como posso ajudar?"}
  ])

  if (!isOpen) return null; 


  return (
    <div className="chat-window">
      <div className="chat-header">ISEL ChatBot 🤖</div>
      <div className="chat-body">
        {messages.map((msg, index)=>(
          <div key = {index} className ={`message ${msg.sender==="user"? "user": "bot"}`}>
            {msg.text}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input type="text" placeholder="Escreva aqui..." />
        <button>➤</button>
      </div>
    </div>
  )
}
