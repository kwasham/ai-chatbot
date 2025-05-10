import type { LanguageModelV1Middleware, LanguageModelV1StreamPart } from 'ai';

// Define the finish reason type manually
type LanguageModelV1FinishReason = 'stop' | 'length' | 'tool-calls' | 'error';

export const fastapiStreamMiddleware: LanguageModelV1Middleware = {
  wrapStream: async ({ doStream, params }) => {
    const { stream, ...rest } = await doStream();

    const transformStream = new TransformStream<
      any, // Your FastAPI backend's stream chunk type
      LanguageModelV1StreamPart
    >({
      transform(chunk, controller) {
        // Transform FastAPI chunk to AI SDK stream part
        if (chunk.type === 'text') {
          controller.enqueue({
            type: 'text-delta',
            textDelta: chunk.content,
          });
        }

        // Handle other potential chunk types
        if (chunk.type === 'finish') {
          controller.enqueue({
            type: 'finish',
            finishReason: (chunk.reason ||
              'stop') as LanguageModelV1FinishReason,
            usage: {
              // Provide default or extracted values
              promptTokens: 0,
              completionTokens: 0,
            },
          });
        }
      },
    });

    return {
      stream: stream.pipeThrough(transformStream),
      ...rest,
    };
  },
};
