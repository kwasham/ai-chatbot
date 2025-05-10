import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { xai } from '@ai-sdk/xai';
import { openai } from '@ai-sdk/openai';
import { isTestEnvironment } from '../constants';
import {
  artifactModel,
  chatModel,
  reasoningModel,
  titleModel,
} from './models.test';

const openaiProvider = createOpenAI({
  baseURL: 'http://localhost:8000',
});

export const myProvider = isTestEnvironment
  ? customProvider({
      languageModels: {
        'chat-model': chatModel,
        'chat-model-reasoning': reasoningModel,
        'title-model': titleModel,
        'artifact-model': artifactModel,
      },
    })
  : customProvider({
      languageModels: {
        'chat-model': openaiProvider.chat('gpt-4o-mini'),
        'chat-model-reasoning': wrapLanguageModel({
          model: openai.responses('gpt-4o-mini'),
          middleware: extractReasoningMiddleware({ tagName: 'think' }),
        }),
        'title-model': openai.responses('gpt-4o-mini'),
        'artifact-model': openai.responses('gpt-4o-mini'),
      },
      imageModels: {
        'small-model': openai.image('dall-e-3'),
      },
    });
