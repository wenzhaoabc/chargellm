import { expect, test } from '@playwright/test'

function openAiStream(content: string) {
  return [
    'data: {"choices":[{"delta":{"role":"assistant"},"finish_reason":null}]}',
    '',
    `data: ${JSON.stringify({ choices: [{ delta: { content }, finish_reason: null }] })}`,
    '',
    'data: [DONE]',
    '',
  ].join('\n')
}

test.describe('电池健康诊断主路径', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.clear()
      window.sessionStorage.clear()
    })
  })

  test('用户通过邀请码进入对话，流式回答可阅读并写入历史', async ({ page }) => {
    const datasetRequests: string[] = []
    const chatPayloads: unknown[] = []

    page.on('request', (request) => {
      if (request.url().includes('/api/datasets')) {
        datasetRequests.push(request.url())
      }
    })

    await page.route('**/api/chat/completions', async (route) => {
      const request = route.request()
      expect(request.url()).not.toContain('session_token')
      expect(request.headers().authorization).toMatch(/^Bearer demo_/)

      const payload = request.postDataJSON()
      chatPayloads.push(payload)
      expect(payload.stream).toBe(true)
      expect(payload.messages).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            role: 'user',
          }),
        ]),
      )
      expect(payload.metadata).toEqual(
        expect.objectContaining({
          dataset_id: expect.any(Number),
        }),
      )

      await route.fulfill({
        status: 200,
        headers: {
          'content-type': 'text/event-stream; charset=utf-8',
          'cache-control': 'no-cache',
        },
        body: openAiStream('诊断结论：当前电池充电曲线表现正常，电压、电流和功率变化稳定，暂未发现明显健康风险。'),
      })
    })

    await page.goto('/')
    await expect(page.getByRole('heading', { name: /电动自行车电池健康诊断大模型/ })).toBeVisible()

    await page.getByRole('button', { name: '立即体验' }).click()
    await page.getByPlaceholder('请输入管理员分配的邀请码').fill('PUBLIC-DEMO-001')
    await page.getByRole('button', { name: '解锁体验' }).click()

    await expect(page).toHaveURL(/\/chat$/)
    await expect(page.getByRole('heading', { name: '电池健康诊断 AI 助手' })).toBeVisible()
    await expect(page.getByText('已连接会话')).toBeVisible()
    await expect(page.getByLabel('添加图片或文件').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /当前数据：/ })).toBeVisible()

    await expect.poll(() => datasetRequests.length).toBeGreaterThan(0)
    expect(datasetRequests.every((url) => !url.includes('session_token'))).toBe(true)

    const composer = page.getByPlaceholder('询问电池老化、故障、容量区间或异常充电过程')
    await composer.fill('这份数据反映了什么健康风险？')
    await page.getByRole('button', { name: '发送' }).click()

    await expect(page.getByText('诊断结论：当前电池充电曲线表现正常')).toBeVisible()
    await expect(page.getByRole('button', { name: '复制回答' })).toBeVisible()
    await expect(page.getByRole('button', { name: '重新生成' })).toBeVisible()

    await expect(page.locator('.conversation-rail')).toContainText('这份数据反映了什么健康风险？')
    await expect(page.locator('.message-list')).not.toContainText('{"answer"')
    expect(chatPayloads).toHaveLength(1)

    await page.getByRole('button', { name: '新建对话' }).first().click()
    await expect(page.locator('.message-list')).toContainText('今天想分析哪组电池数据？')
    await expect(page.locator('.conversation-rail')).toContainText('这份数据反映了什么健康风险？')
  })
})
