import '@testing-library/jest-dom/vitest'

const memoryStore = new Map<string, string>()

Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: (key: string) => memoryStore.get(key) ?? null,
    setItem: (key: string, value: string) => memoryStore.set(key, value),
    removeItem: (key: string) => memoryStore.delete(key),
    clear: () => memoryStore.clear(),
  },
  configurable: true,
})
