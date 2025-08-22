import axios from 'axios';

const apiUrl = process.env.NEXT_PUBLIC_API_URL;
const apiKey = process.env.NEXT_PUBLIC_API_KEY;

if (!apiUrl) {
  throw new Error("NEXT_PUBLIC_API_URL is not defined");
}

if (!apiKey) {
  throw new Error("NEXT_PUBLIC_API_KEY is not defined");
}

export const api = axios.create({
  baseURL: apiUrl,
  headers: {
    "X-API-Key": apiKey,
  },
});

export const fetcher = (url: string) => api.get(url).then((res: { data: any; }) => res.data);