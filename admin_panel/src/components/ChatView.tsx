import { useEffect, useRef } from 'react'
import { Message } from '../services/messagesApi'
import { format } from 'date-fns'

interface ChatViewProps {
  messages: Message[]
}

export default function ChatView({ messages }: ChatViewProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  return (
    <div className="flex flex-col h-[600px] bg-gray-100 rounded-lg p-4 overflow-y-auto">
      {messages.map((message) => {
        const isBot = message.is_bot === 1
        const isUser = !isBot
        
        return (
          <div
            key={message.id}
            className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                isUser
                  ? 'bg-primary-blue text-white rounded-br-none'
                  : 'bg-primary-yellow text-gray-900 rounded-bl-none'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.text}</p>
              <p
                className={`text-xs mt-1 ${
                  isUser ? 'text-blue-100' : 'text-gray-600'
                }`}
              >
                {format(new Date(new Date(message.created_at).toLocaleString('en-US', { timeZone: 'Europe/Moscow' })), 'HH:mm')}
              </p>
            </div>
          </div>
        )
      })}
      <div ref={messagesEndRef} />
    </div>
  )
}

