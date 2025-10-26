interface SuccessBannerProps {
  message: string;
  onDismiss: () => void;
}

export function SuccessBanner({ message, onDismiss }: SuccessBannerProps) {
  return (
    <div className="mb-2 rounded-md border border-green-200 bg-green-50 p-2 text-sm text-green-700">
      <div className="flex items-center justify-between">
        <span>✅ {message}</span>
        <button className="underline" onClick={onDismiss}>
          Dismiss
        </button>
      </div>
    </div>
  );
}
