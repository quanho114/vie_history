import type { Preview } from '@storybook/react';
import '../src/index.css';

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i
      }
    },
    backgrounds: {
      default: 'light',
      values: [
        { name: 'light', value: '#faf9f5' },
        { name: 'dark', value: '#141413' }
      ]
    },
    viewport: {
      viewports: {
        mobile: {
          name: 'Mobile',
          styles: {
            width: '375px',
            height: '812px'
          }
        },
        tablet: {
          name: 'Tablet',
          styles: {
            width: '768px',
            height: '1024px'
          }
        },
        desktop: {
          name: 'Desktop',
          styles: {
            width: '1280px',
            height: '800px'
          }
        }
      }
    },
    layout: 'centered'
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals?.backgrounds?.value === '#141413' ? 'dark' : 'light';

      return (
        <div
          data-theme={theme}
          style={{
            padding: '24px',
            minHeight: '100px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <Story />
        </div>
      );
    }
  ],
  tags: ['autodocs']
};

export default preview;
