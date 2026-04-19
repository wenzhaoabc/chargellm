import { describe, expect, it } from 'vitest'
import { consumeSseStream } from './chat'

function streamFromText(text: string) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(text))
      controller.close()
    },
  })
}

describe('consumeSseStream', () => {
  it('emits long token payloads in smaller visible chunks', async () => {
    const tokenMessages: string[] = []
    await consumeSseStream(
      streamFromText('event: token\ndata: {"text":"模型正在逐步输出诊断结论"}\n\n'),
      {
        onEvent: (event) => {
          if (event.type === 'token') {
            tokenMessages.push(event.message)
          }
        },
      },
    )

    expect(tokenMessages.length).toBeGreaterThan(1)
    expect(tokenMessages.join('')).toBe('模型正在逐步输出诊断结论')
  })

  it('accepts OpenAI chat completion chunks', async () => {
    const tokenMessages: string[] = []
    await consumeSseStream(
      streamFromText(
        [
          'data: {"choices":[{"delta":{"role":"assistant","content":"第一段"}}]}',
          '',
          'data: {"choices":[{"delta":{"content":"第二段"},"finish_reason":null}]}',
          '',
          'data: [DONE]',
          '',
        ].join('\n'),
      ),
      {
        onEvent: (event) => {
          if (event.type === 'token') {
            tokenMessages.push(event.message)
          }
        },
      },
    )

    expect(tokenMessages.join('')).toBe('第一段第二段')
  })

  it('renders the answer field when a compatible model still returns JSON text', async () => {
    const tokenMessages: string[] = []
    const firstChunk = JSON.stringify({ choices: [{ delta: { content: '{"answer":"诊断' } }] })
    const secondChunk = JSON.stringify({ choices: [{ delta: { content: '结论"}' } }] })
    await consumeSseStream(
      streamFromText(
        [
          `data: ${firstChunk}`,
          '',
          `data: ${secondChunk}`,
          '',
          'data: [DONE]',
          '',
        ].join('\n'),
      ),
      {
        onEvent: (event) => {
          if (event.type === 'token') {
            tokenMessages.push(event.message)
          }
        },
      },
    )

    expect(tokenMessages.join('')).toBe('诊断结论')
    expect(tokenMessages.join('')).not.toContain('"answer"')
  })
})
