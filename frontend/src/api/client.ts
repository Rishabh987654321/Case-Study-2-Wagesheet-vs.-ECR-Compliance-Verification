import axios from "axios"

export const apiClient = axios.create({
  baseURL: "/api",
})

export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = "ApiError"
    this.code = code
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.error && error.response?.data?.detail) {
      return Promise.reject(new ApiError(error.response.data.error, error.response.data.detail))
    }
    if (error.code === "ERR_NETWORK" || !error.response) {
      return Promise.reject(new ApiError("NETWORK_ERROR", "Cannot connect to server"))
    }
    return Promise.reject(error)
  },
)
