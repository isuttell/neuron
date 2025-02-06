import { getAccessToken } from "@/actions/getToken";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };
type RequestData = Record<string, JsonValue> | FormData;

class ApiClient {
  private baseUrl: string = "/api";

  private async getHeaders(isFormData = false): Promise<HeadersInit> {
    const accessToken = await getAccessToken();
    const headers: HeadersInit = {
      Authorization: `Bearer ${accessToken}`,
    };
    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, { headers });
    return this.handleResponse<T>(response);
  }

  async post<T>(endpoint: string, data: RequestData): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers = await this.getHeaders(isFormData);
    const body = isFormData ? data : JSON.stringify(data);
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "POST",
      headers,
      body,
    });
    return this.handleResponse<T>(response);
  }

  async put<T>(endpoint: string, data: RequestData): Promise<T> {
    const isFormData = data instanceof FormData;
    const headers = await this.getHeaders(isFormData);
    const body = isFormData ? data : JSON.stringify(data);
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "PUT",
      headers,
      body,
    });
    return this.handleResponse<T>(response);
  }

  async delete<T>(endpoint: string): Promise<T> {
    const headers = await this.getHeaders();
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: "DELETE",
      headers,
    });
    return this.handleResponse<T>(response);
  }
}

export const api = new ApiClient();
