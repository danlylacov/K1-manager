import { useQuery, useMutation } from '@tanstack/react-query'
import { usersApi } from '../services/usersApi'
import { messagesApi } from '../services/messagesApi'
import EmojiPicker from '../components/EmojiPicker'
import { useState } from 'react'

export default function BroadcastPage() {
  const [selectedUsers, setSelectedUsers] = useState<Set<number>>(new Set())
  const [messageText, setMessageText] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [scheduledAt, setScheduledAt] = useState('')
  const [broadcastType, setBroadcastType] = useState<'immediate' | 'scheduled'>('immediate')
  
  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.getAll,
  })
  
  const broadcastMutation = useMutation({
    mutationFn: async () => {
      const telegramIds = Array.from(selectedUsers)
      if (broadcastType === 'scheduled' && scheduledAt) {
        await messagesApi.scheduleBroadcast({
          telegram_ids: telegramIds,
          text: messageText,
          scheduled_at: scheduledAt,
          files: selectedFiles.length > 0 ? selectedFiles : undefined,
        })
      } else {
        await messagesApi.broadcast({
          telegram_ids: telegramIds,
          text: messageText,
          files: selectedFiles.length > 0 ? selectedFiles : undefined,
        })
      }
    },
    onSuccess: () => {
      setMessageText('')
      setSelectedFiles([])
      setScheduledAt('')
      setSelectedUsers(new Set())
      alert('Рассылка отправлена!')
    },
  })
  
  const toggleUser = (telegramId: number) => {
    const newSelected = new Set(selectedUsers)
    if (newSelected.has(telegramId)) {
      newSelected.delete(telegramId)
    } else {
      newSelected.add(telegramId)
    }
    setSelectedUsers(newSelected)
  }
  
  const selectAll = () => {
    if (users) {
      setSelectedUsers(new Set(users.map(u => u.telegram_id)))
    }
  }
  
  const deselectAll = () => {
    setSelectedUsers(new Set())
  }
  
  return (
    <div>
      <h1 className="text-3xl font-bold text-primary-blue mb-6">Рассылки</h1>
      
      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">Тип рассылки</h2>
        <div className="flex space-x-4 mb-4">
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              value="immediate"
              checked={broadcastType === 'immediate'}
              onChange={(e) => setBroadcastType(e.target.value as 'immediate')}
            />
            <span>Немедленная</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              value="scheduled"
              checked={broadcastType === 'scheduled'}
              onChange={(e) => setBroadcastType(e.target.value as 'scheduled')}
            />
            <span>Запланированная</span>
          </label>
        </div>
        
        {broadcastType === 'scheduled' && (
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Дата и время</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              className="input-field"
            />
          </div>
        )}
      </div>
      
      <div className="card mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Выбор получателей</h2>
          <div className="space-x-2">
            <button onClick={selectAll} className="btn-secondary text-sm">
              Выбрать всех
            </button>
            <button onClick={deselectAll} className="btn-primary text-sm">
              Снять выбор
            </button>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Выбрано: {selectedUsers.size} пользователей
        </p>
        <div className="max-h-64 overflow-y-auto border rounded-lg p-4">
          {users?.map((user) => (
            <label key={user.id} className="flex items-center space-x-2 py-2 hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedUsers.has(user.telegram_id)}
                onChange={() => toggleUser(user.telegram_id)}
              />
              <span>
                {user.username ? `@${user.username}` : `#${user.telegram_id}`}
                {user.phone && ` (${user.phone})`}
              </span>
            </label>
          ))}
        </div>
      </div>
      
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Сообщение</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (selectedUsers.size > 0 && (messageText.trim() || selectedFiles.length > 0)) {
              broadcastMutation.mutate()
            }
          }}
          className="space-y-4"
        >
          <div className="relative">
            <textarea
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              placeholder="Введите текст сообщения..."
              className="input-field pr-10"
              rows={5}
            />
            <div className="absolute bottom-2 right-2">
              <EmojiPicker
                onEmojiSelect={(emoji) => {
                  setMessageText((prev) => prev + emoji)
                }}
              />
            </div>
          </div>
          <div>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={(e) => {
                if (e.target.files) {
                  const filesArray = Array.from(e.target.files)
                  setSelectedFiles((prev) => [...prev, ...filesArray])
                }
              }}
              className="input-field"
            />
            {selectedFiles.length > 0 && (
              <div className="mt-2 space-y-2">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center space-x-2 p-2 bg-gray-100 rounded">
                    {file.type.startsWith('image/') && (
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="w-16 h-16 object-cover rounded"
                      />
                    )}
                    <div className="flex-1">
                      <p className="text-sm text-gray-700">{file.name}</p>
                      <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedFiles((prev) => prev.filter((_, i) => i !== index))}
                      className="text-red-600 hover:text-red-800"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={
              broadcastMutation.isPending ||
              selectedUsers.size === 0 ||
              (!messageText.trim() && selectedFiles.length === 0) ||
              (broadcastType === 'scheduled' && !scheduledAt)
            }
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {broadcastMutation.isPending
              ? 'Отправка...'
              : broadcastType === 'scheduled'
              ? 'Запланировать рассылку'
              : 'Отправить рассылку'}
          </button>
        </form>
      </div>
    </div>
  )
}

