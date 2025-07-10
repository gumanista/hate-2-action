export const fetcher = async (resource: string) => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;

  if (!apiUrl) {
    throw new Error("NEXT_PUBLIC_API_URL is not defined");
  }

  if (!apiKey) {
    throw new Error("NEXT_PUBLIC_API_KEY is not defined");
  }

  const response = await fetch(`${apiUrl}${resource}`, {
    headers: {
      "X-API-Key": apiKey,
    },
  });

  if (!response.ok) {
    throw new Error("An error occurred while fetching the data.");
  }

  return response.json();
};