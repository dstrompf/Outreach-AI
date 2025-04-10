
export async function generateKnowledgeBaseSuggestion(promptText) {
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${import.meta.env.VITE_OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gpt-3.5-turbo',
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant that improves knowledge base instructions to be clear, professional, and helpful.',
        },
        {
          role: 'user',
          content: promptText,
        },
      ],
      temperature: 0.7,
      max_tokens: 300,
    }),
  });

  const data = await response.json();
  return data.choices[0]?.message?.content.trim();
}
