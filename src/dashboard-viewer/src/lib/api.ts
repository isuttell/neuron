export async function checkETag(url: string): Promise<string | null> {
  try {
    const response = await fetch(url, {
      method: 'HEAD',
      cache: 'no-cache',
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.headers.get('etag')
  } catch (error) {
    console.error('Failed to check ETag:', error)
    throw error
  }
}

export function preloadImage(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve()
    img.onerror = reject
    img.src = url
  })
}
