import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: [
    '../src/**/*.mdx',
    '../src/**/*.stories.@(js|jsx|ts|tsx)'
  ],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y',
    '@storybook/addon-interactions',
    '@storybook/addon-docs'
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {}
  },
  docs: {
    autodocs: 'tag'
  },
  viteFinal: async (config) => {
    return {
      ...config,
      server: {
        port: 6006,
        host: true
      },
      build: {
        ...config.build,
        rollupOptions: {
          ...config.build?.rollupOptions,
          output: {
            manualChunks: {
              'vendor-react': ['react', 'react-dom'],
              'vendor-animation': ['framer-motion'],
              'vendor-three': ['three', '@react-three/fiber', '@react-three/drei']
            }
          }
        }
      }
    };
  }
};

export default config;
