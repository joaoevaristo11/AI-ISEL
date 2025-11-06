import React, { useState, useRef, useEffect } from "react"
import "./ChatWindow.css"

export default function ChatWindow({ isOpen }) {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "👋 Olá! Como posso ajudar?" },
  ])

  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false) // ⬅️ novo estado


  const messagesEndRef = useRef(null)

  // ✅ Todos os hooks são sempre chamados, independentemente do isOpen
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isTyping])

  // 🔽 só aqui verificamos o isOpen
  if (!isOpen) return null

  const handleSendMessage = async () => {
    const trimmedInput = inputValue.trim()
    if (!trimmedInput) return

    setMessages((prev) => [...prev, { sender: "user", text: trimmedInput }])
    setInputValue("")
    setIsTyping(true) 

    try{
      const botReply = await sendToBackEnd(trimmedInput)
      setMessages((prev)=>[...prev,{sender: "bot", text: botReply}])
    }catch(err){
      setMessages((prev)=>[...prev, {sender: "bot", text: "❌ Erro ao responder. Tenta novamente."}])
    }finally{
      setIsTyping(false)  
    }

  }

  const handleEnter = (e) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleSendMessage()
    }
  }

    // 🔮 Função de resposta simulada (mock)
  const getFakeResponse = (userMsg) => {
    const lower = userMsg.toLowerCase()
    if (lower.includes("olá") || lower.includes("ola"))
      return "Olá! 😊 Como estás hoje?"
    if (lower.includes("isel")) return "O ISEL é uma excelente escolha! 🎓"
    if (lower.includes("obrigado"))
      return "De nada! Estou aqui para ajudar. 🤖"
    return "Interessante... conta-me mais sobre isso!"
  }

  async function sendToBackEnd(userMsg){
    try{
      const res = await fetch("http://localhost:5000/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: userMsg})
      })

      if(!res.ok) throw new Error("Erro no servidor...")

      const data = await res.json()

      // ✅ Quando backend estiver pronto, espera que devolva { reply: "..." }
      return data.reply || "Sem resposta definida no backend."
    }catch(err){
      console.warn("Backend não disponível, usando mock:", err)

      return getFakeResponse(userMsg)
    }
  }

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

         {/* 💭 Indicador “a escrever...” */}
        {isTyping && (
          <div className="message bot typing">💭 ISEL ChatBot está a responder...</div>
        )}

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
  )
}
