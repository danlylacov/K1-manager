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
    <div className="flex flex-col h-[400px] sm:h-[500px] md:h-[600px] bg-gray-100 rounded-lg p-2 sm:p-4 overflow-y-auto">
      {messages.map((message) => {
        const isBot = message.is_bot === 1
        const isUser = !isBot
        
        return (
          <div
            key={message.id}
            className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] sm:max-w-xs lg:max-w-md px-3 sm:px-4 py-2 rounded-lg ${
                isUser
                  ? 'bg-primary-blue text-white rounded-br-none'
                  : 'bg-primary-yellow text-gray-900 rounded-bl-none'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.text}</p>
              <div className="flex items-center justify-between mt-1">
                <p
                  className={`text-xs ${
                    isUser ? 'text-blue-100' : 'text-gray-600'
                  }`}
                >
                  {format(new Date(new Date(message.created_at).toLocaleString('en-US', { timeZone: 'Europe/Moscow' })), 'HH:mm')}
                </p>
                {isUser && message.relevance !== null && message.relevance !== undefined && (
                  <span className="text-xs px-2 py-0.5 rounded bg-white bg-opacity-20 text-blue-100">
                    Релевантность: {message.relevance > 1 ? message.relevance.toFixed(1) : (message.relevance * 100).toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        )
      })}
      <div ref={messagesEndRef} />
    </div>
  )
}

