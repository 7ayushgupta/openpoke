import clsx from 'clsx';
import { RefObject } from 'react';
import ReactMarkdown from 'react-markdown';

import type { ChatBubble } from './types';

interface ChatMessagesProps {
  messages: ReadonlyArray<ChatBubble>;
  isWaitingForResponse: boolean;
  scrollContainerRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
}

export function ChatMessages({ messages, isWaitingForResponse, scrollContainerRef, onScroll }: ChatMessagesProps) {
  return (
    <div ref={scrollContainerRef} onScroll={onScroll} className="flex h-[70vh] flex-col gap-2 overflow-y-auto p-4">
      {messages.length === 0 && <EmptyState />}

      {messages.map((message, index) => {
        const isUser = message.role === 'user';
        const isDraft = message.role === 'draft';
        const next = messages[index + 1];
        const tail = !next || next.role !== message.role;

        return (
          <div key={message.id} className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
            <div
              className={clsx(
                isUser ? 'bubble-out' : 'bubble-in',
                tail ? (isUser ? 'bubble-tail-out' : 'bubble-tail-in') : '',
                isDraft && 'whitespace-pre-wrap',
                'markdown-content',
              )}
            >
              <div className={clsx(isDraft ? 'block whitespace-pre-wrap' : 'whitespace-pre-wrap')}>
                <ReactMarkdown
                  components={{
                    p: ({ children }) => <p className="my-1 first:mt-0 last:mb-0">{children}</p>,
                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                    em: ({ children }) => <em className="italic">{children}</em>,
                    ul: ({ children }) => <ul className="my-1 ml-4 list-disc space-y-0.5">{children}</ul>,
                    ol: ({ children }) => <ol className="my-1 ml-4 list-decimal space-y-0.5">{children}</ol>,
                    li: ({ children }) => <li className="pl-1">{children}</li>,
                    code: ({ children }) => (
                      <code className="rounded bg-black/10 px-1 py-0.5 text-xs font-mono">{children}</code>
                    ),
                    pre: ({ children }) => (
                      <pre className="my-1 overflow-x-auto rounded bg-black/10 p-2 text-xs">{children}</pre>
                    ),
                    h1: ({ children }) => <h1 className="my-2 text-base font-bold">{children}</h1>,
                    h2: ({ children }) => <h2 className="my-2 text-sm font-bold">{children}</h2>,
                    h3: ({ children }) => <h3 className="my-1.5 text-sm font-semibold">{children}</h3>,
                    blockquote: ({ children }) => (
                      <blockquote className="my-1 border-l-2 border-current/30 pl-2 italic">{children}</blockquote>
                    ),
                    a: ({ children, href }) => (
                      <a href={href} className="underline hover:opacity-80" target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    ),
                  }}
                >
                  {message.text}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        );
      })}

      {isWaitingForResponse && <TypingIndicator />}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bubble-in bubble-tail-in">
        <div className="flex items-center space-x-1">
          <div className="flex space-x-1">
            <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mx-auto my-12 max-w-sm text-center text-gray-500">
      <h2 className="mb-2 text-xl font-semibold text-gray-700">Start a conversation</h2>
      <p className="text-sm">
        Your messages will appear here. Send something to get started.
      </p>
    </div>
  );
}
