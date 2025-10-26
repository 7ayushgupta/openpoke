import { useState } from 'react';

interface ChatHeaderProps {
  onOpenSettings: () => void;
  onClearHistory: () => void;
}

export function ChatHeader({ onOpenSettings, onClearHistory }: ChatHeaderProps) {
  const [showConfirmClear, setShowConfirmClear] = useState(false);

  const handleClearClick = () => {
    setShowConfirmClear(true);
  };

  const handleConfirmClear = () => {
    onClearHistory();
    setShowConfirmClear(false);
  };

  const handleCancelClear = () => {
    setShowConfirmClear(false);
  };

  return (
    <header className="mb-4 flex items-center justify-between">
      <div className="flex items-center">
        <h1 className="text-lg font-semibold">OpenPoke 🌴</h1>
      </div>
      <div className="flex items-center gap-2">
        <button
          className="rounded-md border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50"
          onClick={onOpenSettings}
        >
          Settings
        </button>
        
        {showConfirmClear ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Clear everything?</span>
            <button
              className="rounded-md bg-red-600 px-3 py-2 text-sm text-white hover:bg-red-700"
              onClick={handleConfirmClear}
            >
              Yes, Clear All
            </button>
            <button
              className="rounded-md border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50"
              onClick={handleCancelClear}
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            className="rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            onClick={handleClearClick}
          >
            Clear All
          </button>
        )}
      </div>
    </header>
  );
}
