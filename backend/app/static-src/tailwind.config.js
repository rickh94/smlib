module.exports = {
  theme: {
    extend: {
      colors: {
        'smoke-darkest': 'rgba(0, 0, 0, 0.9)',
        'smoke-darker': 'rgba(0, 0, 0, 0.75)',
        'smoke-dark': 'rgba(0, 0, 0, 0.6)',
        'smoke': 'rgba(0, 0, 0, 0.5)',
        'smoke-light': 'rgba(0, 0, 0, 0.4)',
        'smoke-lighter': 'rgba(0, 0, 0, 0.25)',
        'smoke-lightest': 'rgba(0, 0, 0, 0.1)',
      },
    },
  },
  variants: {
    padding: ['last', 'responsive', 'hover', 'focus', 'first'],
    borderWidth: ['last', 'first', 'responsive', 'hover', 'focus'],
    borderColor: ['last', 'responsive', 'hover', 'focus', 'first', 'focus-within', 'even', 'odd'],
    backgroundColor: ['last', 'first', 'hover', 'focus', 'even', 'odd'],
  },
  plugins: [],
};
