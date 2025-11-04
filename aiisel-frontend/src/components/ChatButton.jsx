import React from "react";
import "./ChatButton.css";
import { MessageCircle, X } from "lucide-react";

function ChatButton({ onClick, isOpen }) {
  return (
    <button className="chat-button" onClick={onClick}>
      {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
    </button>
  );
}

export default ChatButton;
