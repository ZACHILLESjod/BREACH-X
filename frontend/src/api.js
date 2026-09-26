const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export async function checkApi() {
  const response = await fetch(`${API_BASE_URL}/`)
  if (!response.ok) throw new Error(`API request failed (${response.status})`)
  return response.json()
}

export async function getAssets(signal) {
  const response = await fetch(`${API_BASE_URL}/assets`, { signal })
  if (!response.ok) {
    let message = `API request failed (${response.status})`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the useful HTTP status if the API returned a non-JSON error.
    }
    throw new Error(message)
  }
  const assets = await response.json()
  if (!Array.isArray(assets)) throw new Error('The asset API returned an invalid response.')
  return assets
}

export async function getAssetExposure(assetId, signal) {
  const encodedId = encodeURIComponent(assetId)
  const response = await fetch(`${API_BASE_URL}/assets/${encodedId}/exposure`, { signal })

  if (!response.ok) {
    let message = `API request failed (${response.status})`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the useful HTTP status if the API returned a non-JSON error.
    }
    throw new Error(message)
  }

  return response.json()
}
