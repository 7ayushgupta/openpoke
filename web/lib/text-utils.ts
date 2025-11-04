/**
 * Text formatting utilities.
 */

/**
 * Format escape characters in text strings.
 * Converts escaped newlines, tabs, carriage returns, and backslashes
 * to their actual characters.
 */
export function formatEscapeCharacters(text: string): string {
  return text
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t')
    .replace(/\\r/g, '\r')
    .replace(/\\\\/g, '\\');
}

