import { useState } from 'react';

interface EmojiPickerProps {
  onEmojiSelect: (emoji: string) => void;
}

const EMOJI_CATEGORIES = {
  'Популярные': ['😀', '😂', '😍', '🥰', '😘', '😊', '😉', '😎', '🤗', '🤔', '😴', '😋', '😝', '🤪', '😜'],
  'Эмоции': ['😃', '😄', '😁', '😆', '😅', '🤣', '🙂', '🙃', '😇', '😊', '😌', '😍', '🥰', '😘', '😗'],
  'Жесты': ['👋', '🤚', '🖐', '✋', '🖖', '👌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆'],
  'Предметы': ['❤️', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖'],
  'Символы': ['✅', '❌', '⭐', '🌟', '💫', '✨', '🔥', '💯', '👍', '👎', '👏', '🙌', '👐', '🤲', '🤝'],
};

export default function EmojiPicker({ onEmojiSelect }: EmojiPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>('Популярные');

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="text-2xl hover:opacity-70 transition-opacity"
        title="Добавить смайлик"
      >
        😊
      </button>
      
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute bottom-full left-0 mb-2 bg-white border border-gray-300 rounded-lg shadow-lg z-20 w-80 max-h-96 overflow-hidden">
            <div className="flex border-b border-gray-200">
              {Object.keys(EMOJI_CATEGORIES).map((category) => (
                <button
                  key={category}
                  type="button"
                  onClick={() => setActiveCategory(category)}
                  className={`px-3 py-2 text-sm font-medium ${
                    activeCategory === category
                      ? 'bg-primary-blue text-white'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
            <div className="p-3 overflow-y-auto max-h-64 grid grid-cols-8 gap-2">
              {EMOJI_CATEGORIES[activeCategory as keyof typeof EMOJI_CATEGORIES].map((emoji, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    onEmojiSelect(emoji);
                    setIsOpen(false);
                  }}
                  className="text-2xl hover:bg-gray-100 rounded p-1 transition-colors"
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

