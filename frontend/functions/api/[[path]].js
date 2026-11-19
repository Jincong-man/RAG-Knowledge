/**
 * Cloudflare Pages Function：把 /api/* 反向代理到 Hugging Face Spaces 后端。
 *
 * Pages 项目环境变量：
 *   BACKEND_URL     必填，例如 https://jincong-rag-knowledge.hf.space
 *   PROXY_SECRET    可选，与后端 PROXY_SECRET 保持一致，用于识别真实用户 IP
 */
export async function onRequest(context) {
  const { request, env } = context
  const backend = (env.BACKEND_URL || '').trim().replace(/\/+$/, '')

  if (!backend) {
    return new Response(
      JSON.stringify({
        detail: '后端未配置：请在 Cloudflare Pages 项目设置中添加环境变量 BACKEND_URL',
      }),
      {
        status: 500,
        headers: { 'content-type': 'application/json; charset=utf-8' },
      },
    )
  }

  const incoming = new URL(request.url)
  const target = new URL(incoming.pathname + incoming.search, backend)

  const headers = new Headers(request.headers)
  headers.delete('host')

  if (env.PROXY_SECRET) {
    headers.set('x-proxy-secret', env.PROXY_SECRET)
  }
  const clientIp = request.headers.get('cf-connecting-ip')
  if (clientIp) {
    headers.set('x-real-ip', clientIp)
  }

  const init = { method: request.method, headers, redirect: 'manual' }
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    init.body = request.body
  }

  const upstream = await fetch(target.toString(), init)

  const responseHeaders = new Headers(upstream.headers)
  // SSE 流式回答不能被边缘缓存
  responseHeaders.set('cache-control', 'no-store')

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  })
}
