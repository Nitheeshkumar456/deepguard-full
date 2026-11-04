export interface StatusResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
}

export interface DetectionResponse {
  is_authentic: boolean;
  confidence: number;
  message: string;
  probabilities?: {
    authentic: number;
    deepfake: number;
  };
}

export type MediaPlatform = 'web' | 'android' | 'api';
