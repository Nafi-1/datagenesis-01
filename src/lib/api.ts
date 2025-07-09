
import axios from 'axios';

const API_BASE_URL = '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export class ApiService {
  static async healthCheck(): Promise<{ healthy: boolean; data?: any }> {
    try {
      const response = await api.get('/health');
      return { 
        healthy: response.status === 200,
        data: response.data
      };
    } catch (error) {
      console.error('Health check failed:', error);
      return { healthy: false };
    }
  }

  static async generateData(prompt: string): Promise<any> {
    try {
      const response = await api.post('/generate', { prompt });
      return response.data;
    } catch (error) {
      console.error('Data generation failed:', error);
      throw error;
    }
  }
}
